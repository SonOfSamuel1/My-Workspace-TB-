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
import { homedir } from "os";

// Gmail API scopes
const SCOPES = [
  "https://www.googleapis.com/auth/gmail.readonly",
  "https://www.googleapis.com/auth/gmail.send",
  "https://www.googleapis.com/auth/gmail.modify",
];

// Token storage path
const TOKEN_PATH = path.join(homedir(), ".gmail-mcp-token.json");
const CREDENTIALS_PATH = path.join(homedir(), ".gmail-mcp-credentials.json");

class GmailMCPServer {
  private server: Server;
  private gmail: any;
  private auth: OAuth2Client | null = null;

  constructor() {
    this.server = new Server(
      {
        name: "gmail-mcp-server",
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

  private async initializeGmailAPI(): Promise<void> {
    try {
      // Load credentials
      if (!fs.existsSync(CREDENTIALS_PATH)) {
        throw new Error(
          `Credentials file not found at ${CREDENTIALS_PATH}. Please follow setup instructions.`
        );
      }

      const credentials = JSON.parse(fs.readFileSync(CREDENTIALS_PATH, "utf-8"));
      const { client_id, client_secret, redirect_uris } = credentials.installed || credentials.web;

      this.auth = new google.auth.OAuth2(client_id, client_secret, redirect_uris[0]);

      // Load token
      if (fs.existsSync(TOKEN_PATH)) {
        const token = JSON.parse(fs.readFileSync(TOKEN_PATH, "utf-8"));
        this.auth.setCredentials(token);
      } else {
        throw new Error(
          `Token file not found at ${TOKEN_PATH}. Please run authentication first.`
        );
      }

      this.gmail = google.gmail({ version: "v1", auth: this.auth });
    } catch (error) {
      console.error("Error initializing Gmail API:", error);
      throw error;
    }
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
    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: this.getTools(),
      };
    });

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      try {
        if (!this.gmail) {
          await this.initializeGmailAPI();
        }

        const { name, arguments: args } = request.params;

        switch (name) {
          case "gmail_list_messages":
            return await this.listMessages(args);
          case "gmail_get_message":
            return await this.getMessage(args);
          case "gmail_send_email":
            return await this.sendEmail(args);
          case "gmail_search_messages":
            return await this.searchMessages(args);
          case "gmail_get_labels":
            return await this.getLabels();
          case "gmail_get_thread":
            return await this.getThread(args);
          case "gmail_trash_message":
            return await this.trashMessage(args);
          case "gmail_mark_as_read":
            return await this.markAsRead(args);
          case "gmail_mark_as_unread":
            return await this.markAsUnread(args);
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
    });
  }

  private getTools(): Tool[] {
    return [
      {
        name: "gmail_list_messages",
        description:
          "List email messages from Gmail. Returns a list of message IDs and snippets. Use maxResults to limit the number of messages (default: 10, max: 100).",
        inputSchema: {
          type: "object",
          properties: {
            maxResults: {
              type: "number",
              description: "Maximum number of messages to return (default: 10, max: 100)",
            },
            labelIds: {
              type: "array",
              items: { type: "string" },
              description: "Only return messages with labels that match all of the specified label IDs (e.g., ['INBOX', 'UNREAD'])",
            },
          },
        },
      },
      {
        name: "gmail_get_message",
        description:
          "Get the full content of a specific email message by ID. Returns the message headers, body, and metadata.",
        inputSchema: {
          type: "object",
          properties: {
            messageId: {
              type: "string",
              description: "The ID of the message to retrieve",
            },
          },
          required: ["messageId"],
        },
      },
      {
        name: "gmail_send_email",
        description:
          "Send an email via Gmail. Supports plain text emails with To, Subject, and Body.",
        inputSchema: {
          type: "object",
          properties: {
            to: {
              type: "string",
              description: "Recipient email address",
            },
            subject: {
              type: "string",
              description: "Email subject",
            },
            body: {
              type: "string",
              description: "Email body (plain text)",
            },
            cc: {
              type: "string",
              description: "CC email addresses (comma-separated)",
            },
            bcc: {
              type: "string",
              description: "BCC email addresses (comma-separated)",
            },
          },
          required: ["to", "subject", "body"],
        },
      },
      {
        name: "gmail_search_messages",
        description:
          "Search for messages using Gmail search syntax (e.g., 'from:someone@example.com', 'subject:meeting', 'is:unread'). Returns matching message IDs and snippets.",
        inputSchema: {
          type: "object",
          properties: {
            query: {
              type: "string",
              description: "Gmail search query (uses Gmail search syntax)",
            },
            maxResults: {
              type: "number",
              description: "Maximum number of messages to return (default: 10, max: 100)",
            },
          },
          required: ["query"],
        },
      },
      {
        name: "gmail_get_labels",
        description:
          "Get all labels in the Gmail account. Returns label IDs, names, and types.",
        inputSchema: {
          type: "object",
          properties: {},
        },
      },
      {
        name: "gmail_get_thread",
        description:
          "Get all messages in an email thread by thread ID. Returns the complete conversation.",
        inputSchema: {
          type: "object",
          properties: {
            threadId: {
              type: "string",
              description: "The ID of the thread to retrieve",
            },
          },
          required: ["threadId"],
        },
      },
      {
        name: "gmail_trash_message",
        description:
          "Move a message to trash by message ID.",
        inputSchema: {
          type: "object",
          properties: {
            messageId: {
              type: "string",
              description: "The ID of the message to trash",
            },
          },
          required: ["messageId"],
        },
      },
      {
        name: "gmail_mark_as_read",
        description:
          "Mark a message as read by removing the UNREAD label.",
        inputSchema: {
          type: "object",
          properties: {
            messageId: {
              type: "string",
              description: "The ID of the message to mark as read",
            },
          },
          required: ["messageId"],
        },
      },
      {
        name: "gmail_mark_as_unread",
        description:
          "Mark a message as unread by adding the UNREAD label.",
        inputSchema: {
          type: "object",
          properties: {
            messageId: {
              type: "string",
              description: "The ID of the message to mark as unread",
            },
          },
          required: ["messageId"],
        },
      },
    ];
  }

  private async listMessages(args: any) {
    const maxResults = args.maxResults || 10;
    const labelIds = args.labelIds || ["INBOX"];

    const response = await this.gmail.users.messages.list({
      userId: "me",
      maxResults: Math.min(maxResults, 100),
      labelIds,
    });

    const messages = response.data.messages || [];

    // Get snippets for each message
    const enrichedMessages = await Promise.all(
      messages.map(async (msg: any) => {
        const details = await this.gmail.users.messages.get({
          userId: "me",
          id: msg.id,
          format: "metadata",
          metadataHeaders: ["From", "Subject", "Date"],
        });

        const headers = details.data.payload.headers;
        const from = headers.find((h: any) => h.name === "From")?.value || "";
        const subject = headers.find((h: any) => h.name === "Subject")?.value || "";
        const date = headers.find((h: any) => h.name === "Date")?.value || "";

        return {
          id: msg.id,
          threadId: msg.threadId,
          snippet: details.data.snippet,
          from,
          subject,
          date,
        };
      })
    );

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            {
              messages: enrichedMessages,
              resultSizeEstimate: response.data.resultSizeEstimate,
            },
            null,
            2
          ),
        },
      ],
    };
  }

  private async getMessage(args: any) {
    const { messageId } = args;

    const response = await this.gmail.users.messages.get({
      userId: "me",
      id: messageId,
      format: "full",
    });

    const message = response.data;
    const headers = message.payload.headers;

    // Extract common headers
    const getHeader = (name: string) =>
      headers.find((h: any) => h.name.toLowerCase() === name.toLowerCase())?.value || "";

    // Extract body
    let body = "";
    const extractBody = (part: any): void => {
      if (part.mimeType === "text/plain" && part.body.data) {
        body += Buffer.from(part.body.data, "base64").toString("utf-8");
      } else if (part.parts) {
        part.parts.forEach(extractBody);
      }
    };

    if (message.payload.body.data) {
      body = Buffer.from(message.payload.body.data, "base64").toString("utf-8");
    } else if (message.payload.parts) {
      message.payload.parts.forEach(extractBody);
    }

    const result = {
      id: message.id,
      threadId: message.threadId,
      labelIds: message.labelIds,
      snippet: message.snippet,
      from: getHeader("From"),
      to: getHeader("To"),
      subject: getHeader("Subject"),
      date: getHeader("Date"),
      body,
    };

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(result, null, 2),
        },
      ],
    };
  }

  private async sendEmail(args: any) {
    const { to, subject, body, cc, bcc } = args;

    // Create email message
    const lines = [
      `To: ${to}`,
      cc ? `Cc: ${cc}` : null,
      bcc ? `Bcc: ${bcc}` : null,
      `Subject: ${subject}`,
      "",
      body,
    ].filter(Boolean);

    const email = lines.join("\n");
    const encodedEmail = Buffer.from(email)
      .toString("base64")
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=+$/, "");

    const response = await this.gmail.users.messages.send({
      userId: "me",
      requestBody: {
        raw: encodedEmail,
      },
    });

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            {
              success: true,
              messageId: response.data.id,
              threadId: response.data.threadId,
            },
            null,
            2
          ),
        },
      ],
    };
  }

  private async searchMessages(args: any) {
    const { query, maxResults = 10 } = args;

    const response = await this.gmail.users.messages.list({
      userId: "me",
      q: query,
      maxResults: Math.min(maxResults, 100),
    });

    const messages = response.data.messages || [];

    // Get details for each message
    const enrichedMessages = await Promise.all(
      messages.map(async (msg: any) => {
        const details = await this.gmail.users.messages.get({
          userId: "me",
          id: msg.id,
          format: "metadata",
          metadataHeaders: ["From", "Subject", "Date"],
        });

        const headers = details.data.payload.headers;
        const from = headers.find((h: any) => h.name === "From")?.value || "";
        const subject = headers.find((h: any) => h.name === "Subject")?.value || "";
        const date = headers.find((h: any) => h.name === "Date")?.value || "";

        return {
          id: msg.id,
          threadId: msg.threadId,
          snippet: details.data.snippet,
          from,
          subject,
          date,
        };
      })
    );

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            {
              query,
              messages: enrichedMessages,
              resultSizeEstimate: response.data.resultSizeEstimate,
            },
            null,
            2
          ),
        },
      ],
    };
  }

  private async getLabels() {
    const response = await this.gmail.users.labels.list({
      userId: "me",
    });

    const labels = response.data.labels || [];

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            {
              labels: labels.map((label: any) => ({
                id: label.id,
                name: label.name,
                type: label.type,
                messageListVisibility: label.messageListVisibility,
                labelListVisibility: label.labelListVisibility,
              })),
            },
            null,
            2
          ),
        },
      ],
    };
  }

  private async getThread(args: any) {
    const { threadId } = args;

    const response = await this.gmail.users.threads.get({
      userId: "me",
      id: threadId,
      format: "full",
    });

    const thread = response.data;
    const messages = thread.messages || [];

    const processedMessages = messages.map((message: any) => {
      const headers = message.payload.headers;
      const getHeader = (name: string) =>
        headers.find((h: any) => h.name.toLowerCase() === name.toLowerCase())?.value || "";

      // Extract body
      let body = "";
      const extractBody = (part: any): void => {
        if (part.mimeType === "text/plain" && part.body.data) {
          body += Buffer.from(part.body.data, "base64").toString("utf-8");
        } else if (part.parts) {
          part.parts.forEach(extractBody);
        }
      };

      if (message.payload.body.data) {
        body = Buffer.from(message.payload.body.data, "base64").toString("utf-8");
      } else if (message.payload.parts) {
        message.payload.parts.forEach(extractBody);
      }

      return {
        id: message.id,
        snippet: message.snippet,
        from: getHeader("From"),
        to: getHeader("To"),
        subject: getHeader("Subject"),
        date: getHeader("Date"),
        body,
      };
    });

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            {
              threadId: thread.id,
              messages: processedMessages,
            },
            null,
            2
          ),
        },
      ],
    };
  }

  private async trashMessage(args: any) {
    const { messageId } = args;

    await this.gmail.users.messages.trash({
      userId: "me",
      id: messageId,
    });

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            {
              success: true,
              messageId,
              action: "trashed",
            },
            null,
            2
          ),
        },
      ],
    };
  }

  private async markAsRead(args: any) {
    const { messageId } = args;

    await this.gmail.users.messages.modify({
      userId: "me",
      id: messageId,
      requestBody: {
        removeLabelIds: ["UNREAD"],
      },
    });

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            {
              success: true,
              messageId,
              action: "marked_as_read",
            },
            null,
            2
          ),
        },
      ],
    };
  }

  private async markAsUnread(args: any) {
    const { messageId } = args;

    await this.gmail.users.messages.modify({
      userId: "me",
      id: messageId,
      requestBody: {
        addLabelIds: ["UNREAD"],
      },
    });

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            {
              success: true,
              messageId,
              action: "marked_as_unread",
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
    console.error("Gmail MCP Server running on stdio");
  }
}

// Run the server
const server = new GmailMCPServer();
server.run().catch(console.error);
