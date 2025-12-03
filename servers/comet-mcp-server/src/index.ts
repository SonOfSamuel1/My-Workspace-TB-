#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ToolSchema,
  TextContent,
  ImageContent,
  Tool
} from '@modelcontextprotocol/sdk/types.js';
import { CometClient, CometResponse } from './comet-client.js';
import path from 'path';
import { promises as fs } from 'fs';

// Initialize Comet client
const cometClient = new CometClient({
  responseTimeout: parseInt(process.env.RESPONSE_TIMEOUT || '30000'),
  stabilizationTime: parseInt(process.env.STABILIZATION_TIME || '1000'),
  maxRetries: parseInt(process.env.MAX_RETRIES || '3'),
  useClipboardFallback: process.env.USE_CLIPBOARD_FALLBACK !== 'false'
});

// Define available tools
const TOOLS: Tool[] = [
  {
    name: 'comet_send_prompt',
    description: 'Send a prompt to Comet assistant and optionally wait for response',
    inputSchema: {
      type: 'object',
      properties: {
        prompt: {
          type: 'string',
          description: 'The prompt text to send to Comet'
        },
        wait_for_response: {
          type: 'boolean',
          description: 'Whether to wait for and return the response',
          default: true
        }
      },
      required: ['prompt']
    }
  },
  {
    name: 'comet_wait_response',
    description: 'Wait for and extract the current response from Comet',
    inputSchema: {
      type: 'object',
      properties: {}
    }
  },
  {
    name: 'comet_navigate',
    description: 'Navigate to a URL in Comet browser',
    inputSchema: {
      type: 'object',
      properties: {
        url: {
          type: 'string',
          description: 'The URL to navigate to'
        }
      },
      required: ['url']
    }
  },
  {
    name: 'comet_extract_page',
    description: 'Extract text content from the current page in Comet',
    inputSchema: {
      type: 'object',
      properties: {}
    }
  },
  {
    name: 'comet_screenshot',
    description: 'Take a screenshot of the Comet browser window',
    inputSchema: {
      type: 'object',
      properties: {
        filename: {
          type: 'string',
          description: 'Filename for the screenshot (without path)',
          default: 'comet-screenshot.png'
        }
      }
    }
  },
  {
    name: 'comet_batch_prompts',
    description: 'Send multiple prompts to Comet sequentially and collect all responses',
    inputSchema: {
      type: 'object',
      properties: {
        prompts: {
          type: 'array',
          items: {
            type: 'string'
          },
          description: 'Array of prompts to send sequentially'
        }
      },
      required: ['prompts']
    }
  },
  {
    name: 'comet_research_topic',
    description: 'Research a topic with optional follow-up questions',
    inputSchema: {
      type: 'object',
      properties: {
        topic: {
          type: 'string',
          description: 'The main topic to research'
        },
        follow_up_questions: {
          type: 'array',
          items: {
            type: 'string'
          },
          description: 'Optional follow-up questions to ask',
          default: []
        }
      },
      required: ['topic']
    }
  },
  {
    name: 'comet_clear',
    description: 'Clear the current Comet conversation',
    inputSchema: {
      type: 'object',
      properties: {}
    }
  },
  {
    name: 'comet_health_check',
    description: 'Check if Comet browser is running and responsive',
    inputSchema: {
      type: 'object',
      properties: {}
    }
  },
  {
    name: 'comet_type_text',
    description: 'Type text at the current cursor position in Comet',
    inputSchema: {
      type: 'object',
      properties: {
        text: {
          type: 'string',
          description: 'The text to type'
        }
      },
      required: ['text']
    }
  },
  {
    name: 'comet_press_enter',
    description: 'Press the Enter key in Comet',
    inputSchema: {
      type: 'object',
      properties: {}
    }
  }
];

// Create MCP server
const server = new Server(
  {
    name: 'comet-mcp-server',
    version: '1.0.0'
  },
  {
    capabilities: {
      tools: {}
    }
  }
);

// Helper function to format response
function formatResponse(response: CometResponse): TextContent[] {
  const content: TextContent[] = [];

  // Add main response text
  content.push({
    type: 'text',
    text: response.text
  });

  // Add URLs if present
  if (response.urls && response.urls.length > 0) {
    content.push({
      type: 'text',
      text: `\n\nFound URLs:\n${response.urls.join('\n')}`
    });
  }

  // Add code blocks if present
  if (response.codeBlocks && response.codeBlocks.length > 0) {
    const codeBlocksText = response.codeBlocks
      .map((block, i) => `Code Block ${i + 1}${block.lang ? ` (${block.lang})` : ''}:\n\`\`\`${block.lang || ''}\n${block.code}\n\`\`\``)
      .join('\n\n');

    content.push({
      type: 'text',
      text: `\n\n${codeBlocksText}`
    });
  }

  return content;
}

// Handle tool listing
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: TOOLS
  };
});

// Handle tool execution
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case 'comet_send_prompt': {
        const { prompt, wait_for_response = true } = args as {
          prompt: string;
          wait_for_response?: boolean;
        };

        const response = await cometClient.sendPrompt(prompt, wait_for_response);

        if (!wait_for_response) {
          return {
            content: [
              {
                type: 'text',
                text: 'Prompt sent successfully'
              }
            ]
          };
        }

        return {
          content: formatResponse(response)
        };
      }

      case 'comet_wait_response': {
        const response = await cometClient.waitForResponse();
        return {
          content: formatResponse(response)
        };
      }

      case 'comet_navigate': {
        const { url } = args as { url: string };
        await cometClient.navigate(url);
        return {
          content: [
            {
              type: 'text',
              text: `Navigated to: ${url}`
            }
          ]
        };
      }

      case 'comet_extract_page': {
        const content = await cometClient.extractPageContent();
        return {
          content: [
            {
              type: 'text',
              text: content
            }
          ]
        };
      }

      case 'comet_screenshot': {
        const { filename = 'comet-screenshot.png' } = args as { filename?: string };

        // Create screenshots directory if it doesn't exist
        const screenshotsDir = path.join(process.cwd(), 'screenshots');
        await fs.mkdir(screenshotsDir, { recursive: true });

        const outputPath = path.join(screenshotsDir, filename);
        await cometClient.takeScreenshot(outputPath);

        return {
          content: [
            {
              type: 'text',
              text: `Screenshot saved to: ${outputPath}`
            }
          ]
        };
      }

      case 'comet_batch_prompts': {
        const { prompts } = args as { prompts: string[] };

        const responses = await cometClient.batchPrompts(prompts);

        const formattedResponses = responses
          .map((response, i) => `### Prompt ${i + 1}:\n${prompts[i]}\n\n### Response:\n${response.text}`)
          .join('\n\n---\n\n');

        return {
          content: [
            {
              type: 'text',
              text: formattedResponses
            }
          ]
        };
      }

      case 'comet_research_topic': {
        const { topic, follow_up_questions = [] } = args as {
          topic: string;
          follow_up_questions?: string[];
        };

        const research = await cometClient.researchTopic(topic, follow_up_questions);

        let resultText = `# Research: ${topic}\n\n`;
        resultText += `## Initial Research:\n${research.initial.text}\n\n`;

        if (research.followUps.length > 0) {
          resultText += `## Follow-up Questions:\n\n`;
          research.followUps.forEach((response, i) => {
            resultText += `### Q${i + 1}: ${follow_up_questions[i]}\n`;
            resultText += `${response.text}\n\n`;
          });
        }

        return {
          content: [
            {
              type: 'text',
              text: resultText
            }
          ]
        };
      }

      case 'comet_clear': {
        await cometClient.clearConversation();
        return {
          content: [
            {
              type: 'text',
              text: 'Comet conversation cleared'
            }
          ]
        };
      }

      case 'comet_health_check': {
        const isHealthy = await cometClient.checkHealth();
        return {
          content: [
            {
              type: 'text',
              text: isHealthy ? 'Comet is running and responsive' : 'Comet is not responsive or not running'
            }
          ]
        };
      }

      case 'comet_type_text': {
        const { text } = args as { text: string };
        await cometClient.typeText(text);
        return {
          content: [
            {
              type: 'text',
              text: `Typed: ${text}`
            }
          ]
        };
      }

      case 'comet_press_enter': {
        await cometClient.pressEnter();
        return {
          content: [
            {
              type: 'text',
              text: 'Enter key pressed'
            }
          ]
        };
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error: any) {
    console.error(`Error executing tool ${name}:`, error);
    return {
      content: [
        {
          type: 'text',
          text: `Error: ${error.message}`
        }
      ],
      isError: true
    };
  }
});

// Start the server
async function main() {
  const transport = new StdioServerTransport();

  console.error('Starting Comet MCP Server...');

  await server.connect(transport);

  console.error('Comet MCP Server running on stdio');
}

// Handle graceful shutdown
process.on('SIGINT', async () => {
  console.error('Shutting down Comet MCP Server...');
  process.exit(0);
});

process.on('SIGTERM', async () => {
  console.error('Shutting down Comet MCP Server...');
  process.exit(0);
});

// Run the server
main().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});