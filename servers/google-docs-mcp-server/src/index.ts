#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from "@modelcontextprotocol/sdk/types.js";
import { google } from "googleapis";
import { OAuth2Client } from "google-auth-library";
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";
import dotenv from "dotenv";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load environment variables
dotenv.config({ path: path.join(__dirname, "../.env") });

interface GoogleDocsConfig {
  credentials: {
    client_id: string;
    client_secret: string;
    redirect_uris: string[];
  };
  token?: {
    access_token: string;
    refresh_token: string;
    scope: string;
    token_type: string;
    expiry_date: number;
  };
}

class GoogleDocsServer {
  private server: Server;
  private auth: OAuth2Client | null = null;
  private docs: any;
  private drive: any;

  constructor() {
    this.server = new Server(
      {
        name: "google-docs-mcp-server",
        version: "1.0.0",
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupHandlers();
    this.setupErrorHandling();
  }

  private async initializeAuth(): Promise<void> {
    const credentialsPath = process.env.GOOGLE_CREDENTIALS_PATH ||
      path.join(__dirname, "../credentials.json");
    const tokenPath = process.env.GOOGLE_TOKEN_PATH ||
      path.join(__dirname, "../token.json");

    if (!fs.existsSync(credentialsPath)) {
      throw new Error(
        `Credentials file not found at ${credentialsPath}. Please follow setup instructions.`
      );
    }

    const credentials = JSON.parse(
      fs.readFileSync(credentialsPath, "utf-8")
    ) as GoogleDocsConfig;

    const { client_id, client_secret, redirect_uris } = credentials.credentials;
    this.auth = new google.auth.OAuth2(
      client_id,
      client_secret,
      redirect_uris[0]
    );

    if (fs.existsSync(tokenPath)) {
      const token = JSON.parse(fs.readFileSync(tokenPath, "utf-8"));
      this.auth.setCredentials(token);
    } else {
      throw new Error(
        `Token file not found at ${tokenPath}. Please run the authorization flow first.`
      );
    }

    this.docs = google.docs({ version: "v1", auth: this.auth });
    this.drive = google.drive({ version: "v3", auth: this.auth });
  }

  private setupErrorHandling(): void {
    this.server.onerror = (error) => {
      console.error("[MCP Error]", error);
    };

    process.on("SIGINT", async () => {
      await this.server.close();
      process.exit(0);
    });
  }

  private setupHandlers(): void {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: this.getTools(),
    }));

    this.server.setRequestHandler(CallToolRequestSchema, async (request) =>
      this.handleToolCall(request)
    );
  }

  private getTools(): Tool[] {
    return [
      {
        name: "create_document",
        description: "Create a new Google Doc with optional title and initial content",
        inputSchema: {
          type: "object",
          properties: {
            title: {
              type: "string",
              description: "Title of the new document",
            },
            content: {
              type: "string",
              description: "Initial text content to add to the document",
            },
          },
        },
      },
      {
        name: "get_document",
        description: "Get the content of a Google Doc by document ID",
        inputSchema: {
          type: "object",
          properties: {
            documentId: {
              type: "string",
              description: "The ID of the Google Doc to retrieve",
            },
          },
          required: ["documentId"],
        },
      },
      {
        name: "update_document",
        description: "Update a Google Doc by appending text or replacing content",
        inputSchema: {
          type: "object",
          properties: {
            documentId: {
              type: "string",
              description: "The ID of the Google Doc to update",
            },
            text: {
              type: "string",
              description: "Text content to add or replace",
            },
            mode: {
              type: "string",
              enum: ["append", "replace"],
              description: "Whether to append text to the end or replace all content (default: append)",
            },
          },
          required: ["documentId", "text"],
        },
      },
      {
        name: "list_documents",
        description: "List Google Docs in your drive (up to 100 most recent)",
        inputSchema: {
          type: "object",
          properties: {
            pageSize: {
              type: "number",
              description: "Number of documents to return (max 100, default 20)",
            },
            query: {
              type: "string",
              description: "Search query to filter documents (e.g., 'name contains \"report\"')",
            },
          },
        },
      },
      {
        name: "search_in_document",
        description: "Search for text within a specific Google Doc",
        inputSchema: {
          type: "object",
          properties: {
            documentId: {
              type: "string",
              description: "The ID of the Google Doc to search",
            },
            searchText: {
              type: "string",
              description: "Text to search for in the document",
            },
          },
          required: ["documentId", "searchText"],
        },
      },
      {
        name: "insert_text",
        description: "Insert text at a specific index in a Google Doc",
        inputSchema: {
          type: "object",
          properties: {
            documentId: {
              type: "string",
              description: "The ID of the Google Doc",
            },
            text: {
              type: "string",
              description: "Text to insert",
            },
            index: {
              type: "number",
              description: "Character index where to insert text (1 is the start of the document body)",
            },
          },
          required: ["documentId", "text", "index"],
        },
      },
      {
        name: "delete_text_range",
        description: "Delete a range of text from a Google Doc",
        inputSchema: {
          type: "object",
          properties: {
            documentId: {
              type: "string",
              description: "The ID of the Google Doc",
            },
            startIndex: {
              type: "number",
              description: "Start index of text to delete",
            },
            endIndex: {
              type: "number",
              description: "End index of text to delete",
            },
          },
          required: ["documentId", "startIndex", "endIndex"],
        },
      },
    ];
  }

  private async handleToolCall(request: any) {
    if (!this.auth) {
      await this.initializeAuth();
    }

    const { name, arguments: args } = request.params;

    try {
      switch (name) {
        case "create_document":
          return await this.createDocument(args);
        case "get_document":
          return await this.getDocument(args);
        case "update_document":
          return await this.updateDocument(args);
        case "list_documents":
          return await this.listDocuments(args);
        case "search_in_document":
          return await this.searchInDocument(args);
        case "insert_text":
          return await this.insertText(args);
        case "delete_text_range":
          return await this.deleteTextRange(args);
        default:
          throw new Error(`Unknown tool: ${name}`);
      }
    } catch (error: any) {
      return {
        content: [
          {
            type: "text",
            text: `Error: ${error.message}`,
          },
        ],
      };
    }
  }

  private async createDocument(args: any) {
    const { title = "Untitled Document", content } = args;

    // Create document
    const response = await this.docs.documents.create({
      requestBody: {
        title,
      },
    });

    const documentId = response.data.documentId;

    // Add initial content if provided
    if (content) {
      await this.docs.documents.batchUpdate({
        documentId,
        requestBody: {
          requests: [
            {
              insertText: {
                location: {
                  index: 1,
                },
                text: content,
              },
            },
          ],
        },
      });
    }

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            {
              documentId,
              title,
              url: `https://docs.google.com/document/d/${documentId}/edit`,
              message: "Document created successfully",
            },
            null,
            2
          ),
        },
      ],
    };
  }

  private async getDocument(args: any) {
    const { documentId } = args;

    const response = await this.docs.documents.get({
      documentId,
    });

    const doc = response.data;
    let text = "";

    // Extract text from document
    if (doc.body?.content) {
      for (const element of doc.body.content) {
        if (element.paragraph?.elements) {
          for (const elem of element.paragraph.elements) {
            if (elem.textRun?.content) {
              text += elem.textRun.content;
            }
          }
        }
      }
    }

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            {
              documentId,
              title: doc.title,
              text,
              url: `https://docs.google.com/document/d/${documentId}/edit`,
            },
            null,
            2
          ),
        },
      ],
    };
  }

  private async updateDocument(args: any) {
    const { documentId, text, mode = "append" } = args;

    const requests: any[] = [];

    if (mode === "replace") {
      // Get document to find the end index
      const doc = await this.docs.documents.get({ documentId });
      const endIndex = doc.data.body.content[doc.data.body.content.length - 1].endIndex - 1;

      // Delete all content except the first character (required by API)
      requests.push({
        deleteContentRange: {
          range: {
            startIndex: 1,
            endIndex: endIndex,
          },
        },
      });

      // Insert new text
      requests.push({
        insertText: {
          location: {
            index: 1,
          },
          text,
        },
      });
    } else {
      // Append mode - insert at end
      requests.push({
        insertText: {
          location: {
            index: 1,
          },
          text,
        },
      });
    }

    await this.docs.documents.batchUpdate({
      documentId,
      requestBody: {
        requests,
      },
    });

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            {
              documentId,
              mode,
              message: "Document updated successfully",
              url: `https://docs.google.com/document/d/${documentId}/edit`,
            },
            null,
            2
          ),
        },
      ],
    };
  }

  private async listDocuments(args: any) {
    const { pageSize = 20, query } = args;

    let q = "mimeType='application/vnd.google-apps.document'";
    if (query) {
      q += ` and ${query}`;
    }

    const response = await this.drive.files.list({
      q,
      pageSize: Math.min(pageSize, 100),
      fields: "files(id, name, createdTime, modifiedTime, webViewLink)",
      orderBy: "modifiedTime desc",
    });

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(response.data.files, null, 2),
        },
      ],
    };
  }

  private async searchInDocument(args: any) {
    const { documentId, searchText } = args;

    const response = await this.docs.documents.get({
      documentId,
    });

    const doc = response.data;
    const matches: any[] = [];
    let currentIndex = 0;

    if (doc.body?.content) {
      for (const element of doc.body.content) {
        if (element.paragraph?.elements) {
          for (const elem of element.paragraph.elements) {
            if (elem.textRun?.content) {
              const content = elem.textRun.content;
              const index = content.toLowerCase().indexOf(searchText.toLowerCase());
              if (index !== -1) {
                matches.push({
                  index: currentIndex + index,
                  text: content.substring(
                    Math.max(0, index - 20),
                    Math.min(content.length, index + searchText.length + 20)
                  ),
                });
              }
              currentIndex += content.length;
            }
          }
        }
      }
    }

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            {
              documentId,
              searchText,
              matchCount: matches.length,
              matches,
            },
            null,
            2
          ),
        },
      ],
    };
  }

  private async insertText(args: any) {
    const { documentId, text, index } = args;

    await this.docs.documents.batchUpdate({
      documentId,
      requestBody: {
        requests: [
          {
            insertText: {
              location: {
                index,
              },
              text,
            },
          },
        ],
      },
    });

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            {
              documentId,
              message: `Inserted text at index ${index}`,
              url: `https://docs.google.com/document/d/${documentId}/edit`,
            },
            null,
            2
          ),
        },
      ],
    };
  }

  private async deleteTextRange(args: any) {
    const { documentId, startIndex, endIndex } = args;

    await this.docs.documents.batchUpdate({
      documentId,
      requestBody: {
        requests: [
          {
            deleteContentRange: {
              range: {
                startIndex,
                endIndex,
              },
            },
          },
        ],
      },
    });

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            {
              documentId,
              message: `Deleted text from index ${startIndex} to ${endIndex}`,
              url: `https://docs.google.com/document/d/${documentId}/edit`,
            },
            null,
            2
          ),
        },
      ],
    };
  }

  async run(): Promise<void> {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("Google Docs MCP Server running on stdio");
  }
}

const server = new GoogleDocsServer();
server.run().catch(console.error);
