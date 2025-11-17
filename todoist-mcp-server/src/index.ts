#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from "@modelcontextprotocol/sdk/types.js";

// Todoist API Base URL
const TODOIST_API_BASE = "https://api.todoist.com/rest/v2";

// Todoist API Client
class TodoistClient {
  private apiToken: string;

  constructor(apiToken: string) {
    this.apiToken = apiToken;
  }

  private async makeRequest(endpoint: string, method: string = "GET", body?: any) {
    const url = `${TODOIST_API_BASE}${endpoint}`;
    const headers: Record<string, string> = {
      "Authorization": `Bearer ${this.apiToken}`,
      "Content-Type": "application/json",
    };

    const options: RequestInit = {
      method,
      headers,
    };

    if (body && (method === "POST" || method === "PUT" || method === "PATCH")) {
      options.body = JSON.stringify(body);
    }

    const response = await fetch(url, options);

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Todoist API error (${response.status}): ${errorText}`);
    }

    // DELETE requests may not return content
    if (method === "DELETE" && response.status === 204) {
      return { success: true };
    }

    return await response.json();
  }

  // Tasks
  async getTasks(params?: {
    project_id?: string;
    section_id?: string;
    label?: string;
    filter?: string;
    lang?: string;
    ids?: string[];
  }) {
    let endpoint = "/tasks";
    if (params) {
      const queryParams = new URLSearchParams();
      if (params.project_id) queryParams.append("project_id", params.project_id);
      if (params.section_id) queryParams.append("section_id", params.section_id);
      if (params.label) queryParams.append("label", params.label);
      if (params.filter) queryParams.append("filter", params.filter);
      if (params.lang) queryParams.append("lang", params.lang);
      if (params.ids) queryParams.append("ids", params.ids.join(","));

      const queryString = queryParams.toString();
      if (queryString) endpoint += `?${queryString}`;
    }
    return this.makeRequest(endpoint);
  }

  async getTask(taskId: string) {
    return this.makeRequest(`/tasks/${taskId}`);
  }

  async createTask(task: {
    content: string;
    description?: string;
    project_id?: string;
    section_id?: string;
    parent_id?: string;
    order?: number;
    labels?: string[];
    priority?: number;
    due_string?: string;
    due_date?: string;
    due_datetime?: string;
    due_lang?: string;
    assignee_id?: string;
  }) {
    return this.makeRequest("/tasks", "POST", task);
  }

  async updateTask(taskId: string, updates: {
    content?: string;
    description?: string;
    labels?: string[];
    priority?: number;
    due_string?: string;
    due_date?: string;
    due_datetime?: string;
    due_lang?: string;
    assignee_id?: string;
  }) {
    return this.makeRequest(`/tasks/${taskId}`, "POST", updates);
  }

  async closeTask(taskId: string) {
    return this.makeRequest(`/tasks/${taskId}/close`, "POST");
  }

  async reopenTask(taskId: string) {
    return this.makeRequest(`/tasks/${taskId}/reopen`, "POST");
  }

  async deleteTask(taskId: string) {
    return this.makeRequest(`/tasks/${taskId}`, "DELETE");
  }

  // Projects
  async getProjects() {
    return this.makeRequest("/projects");
  }

  async getProject(projectId: string) {
    return this.makeRequest(`/projects/${projectId}`);
  }

  async createProject(project: {
    name: string;
    parent_id?: string;
    color?: string;
    is_favorite?: boolean;
    view_style?: string;
  }) {
    return this.makeRequest("/projects", "POST", project);
  }

  async updateProject(projectId: string, updates: {
    name?: string;
    color?: string;
    is_favorite?: boolean;
    view_style?: string;
  }) {
    return this.makeRequest(`/projects/${projectId}`, "POST", updates);
  }

  async deleteProject(projectId: string) {
    return this.makeRequest(`/projects/${projectId}`, "DELETE");
  }

  // Sections
  async getSections(projectId?: string) {
    let endpoint = "/sections";
    if (projectId) {
      endpoint += `?project_id=${projectId}`;
    }
    return this.makeRequest(endpoint);
  }

  async getSection(sectionId: string) {
    return this.makeRequest(`/sections/${sectionId}`);
  }

  async createSection(section: {
    name: string;
    project_id: string;
    order?: number;
  }) {
    return this.makeRequest("/sections", "POST", section);
  }

  async updateSection(sectionId: string, name: string) {
    return this.makeRequest(`/sections/${sectionId}`, "POST", { name });
  }

  async deleteSection(sectionId: string) {
    return this.makeRequest(`/sections/${sectionId}`, "DELETE");
  }

  // Comments
  async getComments(params: { task_id?: string; project_id?: string }) {
    let endpoint = "/comments";
    const queryParams = new URLSearchParams();
    if (params.task_id) queryParams.append("task_id", params.task_id);
    if (params.project_id) queryParams.append("project_id", params.project_id);

    const queryString = queryParams.toString();
    if (queryString) endpoint += `?${queryString}`;

    return this.makeRequest(endpoint);
  }

  async getComment(commentId: string) {
    return this.makeRequest(`/comments/${commentId}`);
  }

  async createComment(comment: {
    task_id?: string;
    project_id?: string;
    content: string;
    attachment?: any;
  }) {
    return this.makeRequest("/comments", "POST", comment);
  }

  async updateComment(commentId: string, content: string) {
    return this.makeRequest(`/comments/${commentId}`, "POST", { content });
  }

  async deleteComment(commentId: string) {
    return this.makeRequest(`/comments/${commentId}`, "DELETE");
  }

  // Labels
  async getLabels() {
    return this.makeRequest("/labels");
  }

  async getLabel(labelId: string) {
    return this.makeRequest(`/labels/${labelId}`);
  }

  async createLabel(label: {
    name: string;
    color?: string;
    order?: number;
    is_favorite?: boolean;
  }) {
    return this.makeRequest("/labels", "POST", label);
  }

  async updateLabel(labelId: string, updates: {
    name?: string;
    color?: string;
    order?: number;
    is_favorite?: boolean;
  }) {
    return this.makeRequest(`/labels/${labelId}`, "POST", updates);
  }

  async deleteLabel(labelId: string) {
    return this.makeRequest(`/labels/${labelId}`, "DELETE");
  }
}

// Define available tools
const tools: Tool[] = [
  // Task Tools
  {
    name: "todoist_get_tasks",
    description: "Get all active tasks, optionally filtered by project, section, label, or filter",
    inputSchema: {
      type: "object",
      properties: {
        project_id: {
          type: "string",
          description: "Filter tasks by project ID",
        },
        section_id: {
          type: "string",
          description: "Filter tasks by section ID",
        },
        label: {
          type: "string",
          description: "Filter tasks by label name",
        },
        filter: {
          type: "string",
          description: "Filter tasks using Todoist filter syntax (e.g., 'today', 'tomorrow', 'p1')",
        },
        ids: {
          type: "array",
          items: { type: "string" },
          description: "Get specific tasks by their IDs",
        },
      },
    },
  },
  {
    name: "todoist_get_task",
    description: "Get a specific task by ID",
    inputSchema: {
      type: "object",
      properties: {
        task_id: {
          type: "string",
          description: "The ID of the task",
        },
      },
      required: ["task_id"],
    },
  },
  {
    name: "todoist_create_task",
    description: "Create a new task",
    inputSchema: {
      type: "object",
      properties: {
        content: {
          type: "string",
          description: "Task content/title",
        },
        description: {
          type: "string",
          description: "Task description (markdown supported)",
        },
        project_id: {
          type: "string",
          description: "Project ID (defaults to Inbox)",
        },
        section_id: {
          type: "string",
          description: "Section ID",
        },
        parent_id: {
          type: "string",
          description: "Parent task ID for creating subtasks",
        },
        labels: {
          type: "array",
          items: { type: "string" },
          description: "Array of label names",
        },
        priority: {
          type: "number",
          description: "Priority from 1 (normal) to 4 (urgent)",
        },
        due_string: {
          type: "string",
          description: "Human-readable due date (e.g., 'tomorrow at 12:00', 'next Monday')",
        },
        due_date: {
          type: "string",
          description: "Due date in YYYY-MM-DD format",
        },
        due_datetime: {
          type: "string",
          description: "Due date and time in RFC3339 format",
        },
      },
      required: ["content"],
    },
  },
  {
    name: "todoist_update_task",
    description: "Update an existing task",
    inputSchema: {
      type: "object",
      properties: {
        task_id: {
          type: "string",
          description: "The ID of the task to update",
        },
        content: {
          type: "string",
          description: "New task content/title",
        },
        description: {
          type: "string",
          description: "New task description",
        },
        labels: {
          type: "array",
          items: { type: "string" },
          description: "New array of label names",
        },
        priority: {
          type: "number",
          description: "New priority from 1 (normal) to 4 (urgent)",
        },
        due_string: {
          type: "string",
          description: "New human-readable due date",
        },
        due_date: {
          type: "string",
          description: "New due date in YYYY-MM-DD format",
        },
      },
      required: ["task_id"],
    },
  },
  {
    name: "todoist_close_task",
    description: "Complete/close a task",
    inputSchema: {
      type: "object",
      properties: {
        task_id: {
          type: "string",
          description: "The ID of the task to close",
        },
      },
      required: ["task_id"],
    },
  },
  {
    name: "todoist_reopen_task",
    description: "Reopen a completed task",
    inputSchema: {
      type: "object",
      properties: {
        task_id: {
          type: "string",
          description: "The ID of the task to reopen",
        },
      },
      required: ["task_id"],
    },
  },
  {
    name: "todoist_delete_task",
    description: "Delete a task",
    inputSchema: {
      type: "object",
      properties: {
        task_id: {
          type: "string",
          description: "The ID of the task to delete",
        },
      },
      required: ["task_id"],
    },
  },
  // Project Tools
  {
    name: "todoist_get_projects",
    description: "Get all projects",
    inputSchema: {
      type: "object",
      properties: {},
    },
  },
  {
    name: "todoist_get_project",
    description: "Get a specific project by ID",
    inputSchema: {
      type: "object",
      properties: {
        project_id: {
          type: "string",
          description: "The ID of the project",
        },
      },
      required: ["project_id"],
    },
  },
  {
    name: "todoist_create_project",
    description: "Create a new project",
    inputSchema: {
      type: "object",
      properties: {
        name: {
          type: "string",
          description: "Project name",
        },
        parent_id: {
          type: "string",
          description: "Parent project ID for creating subprojects",
        },
        color: {
          type: "string",
          description: "Color name (e.g., 'berry_red', 'blue', 'green')",
        },
        is_favorite: {
          type: "boolean",
          description: "Whether the project is a favorite",
        },
        view_style: {
          type: "string",
          description: "View style: 'list' or 'board'",
        },
      },
      required: ["name"],
    },
  },
  {
    name: "todoist_update_project",
    description: "Update an existing project",
    inputSchema: {
      type: "object",
      properties: {
        project_id: {
          type: "string",
          description: "The ID of the project to update",
        },
        name: {
          type: "string",
          description: "New project name",
        },
        color: {
          type: "string",
          description: "New color name",
        },
        is_favorite: {
          type: "boolean",
          description: "Whether the project is a favorite",
        },
        view_style: {
          type: "string",
          description: "View style: 'list' or 'board'",
        },
      },
      required: ["project_id"],
    },
  },
  {
    name: "todoist_delete_project",
    description: "Delete a project",
    inputSchema: {
      type: "object",
      properties: {
        project_id: {
          type: "string",
          description: "The ID of the project to delete",
        },
      },
      required: ["project_id"],
    },
  },
  // Section Tools
  {
    name: "todoist_get_sections",
    description: "Get all sections, optionally filtered by project",
    inputSchema: {
      type: "object",
      properties: {
        project_id: {
          type: "string",
          description: "Filter sections by project ID",
        },
      },
    },
  },
  {
    name: "todoist_create_section",
    description: "Create a new section in a project",
    inputSchema: {
      type: "object",
      properties: {
        name: {
          type: "string",
          description: "Section name",
        },
        project_id: {
          type: "string",
          description: "The project ID where the section will be created",
        },
        order: {
          type: "number",
          description: "Order of the section",
        },
      },
      required: ["name", "project_id"],
    },
  },
  {
    name: "todoist_update_section",
    description: "Update a section name",
    inputSchema: {
      type: "object",
      properties: {
        section_id: {
          type: "string",
          description: "The ID of the section to update",
        },
        name: {
          type: "string",
          description: "New section name",
        },
      },
      required: ["section_id", "name"],
    },
  },
  {
    name: "todoist_delete_section",
    description: "Delete a section",
    inputSchema: {
      type: "object",
      properties: {
        section_id: {
          type: "string",
          description: "The ID of the section to delete",
        },
      },
      required: ["section_id"],
    },
  },
  // Comment Tools
  {
    name: "todoist_get_comments",
    description: "Get all comments for a task or project",
    inputSchema: {
      type: "object",
      properties: {
        task_id: {
          type: "string",
          description: "Get comments for a specific task",
        },
        project_id: {
          type: "string",
          description: "Get comments for a specific project",
        },
      },
    },
  },
  {
    name: "todoist_create_comment",
    description: "Create a new comment on a task or project",
    inputSchema: {
      type: "object",
      properties: {
        task_id: {
          type: "string",
          description: "The task ID to comment on",
        },
        project_id: {
          type: "string",
          description: "The project ID to comment on",
        },
        content: {
          type: "string",
          description: "Comment content (markdown supported)",
        },
      },
      required: ["content"],
    },
  },
  {
    name: "todoist_update_comment",
    description: "Update a comment",
    inputSchema: {
      type: "object",
      properties: {
        comment_id: {
          type: "string",
          description: "The ID of the comment to update",
        },
        content: {
          type: "string",
          description: "New comment content",
        },
      },
      required: ["comment_id", "content"],
    },
  },
  {
    name: "todoist_delete_comment",
    description: "Delete a comment",
    inputSchema: {
      type: "object",
      properties: {
        comment_id: {
          type: "string",
          description: "The ID of the comment to delete",
        },
      },
      required: ["comment_id"],
    },
  },
  // Label Tools
  {
    name: "todoist_get_labels",
    description: "Get all labels",
    inputSchema: {
      type: "object",
      properties: {},
    },
  },
  {
    name: "todoist_create_label",
    description: "Create a new label",
    inputSchema: {
      type: "object",
      properties: {
        name: {
          type: "string",
          description: "Label name",
        },
        color: {
          type: "string",
          description: "Color name (e.g., 'berry_red', 'blue', 'green')",
        },
        is_favorite: {
          type: "boolean",
          description: "Whether the label is a favorite",
        },
      },
      required: ["name"],
    },
  },
  {
    name: "todoist_update_label",
    description: "Update a label",
    inputSchema: {
      type: "object",
      properties: {
        label_id: {
          type: "string",
          description: "The ID of the label to update",
        },
        name: {
          type: "string",
          description: "New label name",
        },
        color: {
          type: "string",
          description: "New color name",
        },
        is_favorite: {
          type: "boolean",
          description: "Whether the label is a favorite",
        },
      },
      required: ["label_id"],
    },
  },
  {
    name: "todoist_delete_label",
    description: "Delete a label",
    inputSchema: {
      type: "object",
      properties: {
        label_id: {
          type: "string",
          description: "The ID of the label to delete",
        },
      },
      required: ["label_id"],
    },
  },
];

// Create server instance
const server = new Server(
  {
    name: "todoist-mcp-server",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Get API token from environment
const apiToken = process.env.TODOIST_API_TOKEN;
if (!apiToken) {
  console.error("Error: TODOIST_API_TOKEN environment variable is required");
  process.exit(1);
}

const client = new TodoistClient(apiToken);

// Handle list_tools request
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools,
  };
});

// Handle call_tool request
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    let result;

    if (!args) {
      throw new Error("Missing arguments for tool call");
    }

    switch (name) {
      // Task operations
      case "todoist_get_tasks":
        result = await client.getTasks({
          project_id: args.project_id as string | undefined,
          section_id: args.section_id as string | undefined,
          label: args.label as string | undefined,
          filter: args.filter as string | undefined,
          ids: args.ids as string[] | undefined,
        });
        break;

      case "todoist_get_task":
        result = await client.getTask(args.task_id as string);
        break;

      case "todoist_create_task":
        result = await client.createTask({
          content: args.content as string,
          description: args.description as string | undefined,
          project_id: args.project_id as string | undefined,
          section_id: args.section_id as string | undefined,
          parent_id: args.parent_id as string | undefined,
          labels: args.labels as string[] | undefined,
          priority: args.priority as number | undefined,
          due_string: args.due_string as string | undefined,
          due_date: args.due_date as string | undefined,
          due_datetime: args.due_datetime as string | undefined,
        });
        break;

      case "todoist_update_task":
        {
          const updates: any = {};
          if (args.content !== undefined) updates.content = args.content;
          if (args.description !== undefined) updates.description = args.description;
          if (args.labels !== undefined) updates.labels = args.labels;
          if (args.priority !== undefined) updates.priority = args.priority;
          if (args.due_string !== undefined) updates.due_string = args.due_string;
          if (args.due_date !== undefined) updates.due_date = args.due_date;

          result = await client.updateTask(args.task_id as string, updates);
        }
        break;

      case "todoist_close_task":
        result = await client.closeTask(args.task_id as string);
        break;

      case "todoist_reopen_task":
        result = await client.reopenTask(args.task_id as string);
        break;

      case "todoist_delete_task":
        result = await client.deleteTask(args.task_id as string);
        break;

      // Project operations
      case "todoist_get_projects":
        result = await client.getProjects();
        break;

      case "todoist_get_project":
        result = await client.getProject(args.project_id as string);
        break;

      case "todoist_create_project":
        result = await client.createProject({
          name: args.name as string,
          parent_id: args.parent_id as string | undefined,
          color: args.color as string | undefined,
          is_favorite: args.is_favorite as boolean | undefined,
          view_style: args.view_style as string | undefined,
        });
        break;

      case "todoist_update_project":
        {
          const updates: any = {};
          if (args.name !== undefined) updates.name = args.name;
          if (args.color !== undefined) updates.color = args.color;
          if (args.is_favorite !== undefined) updates.is_favorite = args.is_favorite;
          if (args.view_style !== undefined) updates.view_style = args.view_style;

          result = await client.updateProject(args.project_id as string, updates);
        }
        break;

      case "todoist_delete_project":
        result = await client.deleteProject(args.project_id as string);
        break;

      // Section operations
      case "todoist_get_sections":
        result = await client.getSections(args.project_id as string | undefined);
        break;

      case "todoist_create_section":
        result = await client.createSection({
          name: args.name as string,
          project_id: args.project_id as string,
          order: args.order as number | undefined,
        });
        break;

      case "todoist_update_section":
        result = await client.updateSection(
          args.section_id as string,
          args.name as string
        );
        break;

      case "todoist_delete_section":
        result = await client.deleteSection(args.section_id as string);
        break;

      // Comment operations
      case "todoist_get_comments":
        result = await client.getComments({
          task_id: args.task_id as string | undefined,
          project_id: args.project_id as string | undefined,
        });
        break;

      case "todoist_create_comment":
        result = await client.createComment({
          task_id: args.task_id as string | undefined,
          project_id: args.project_id as string | undefined,
          content: args.content as string,
        });
        break;

      case "todoist_update_comment":
        result = await client.updateComment(
          args.comment_id as string,
          args.content as string
        );
        break;

      case "todoist_delete_comment":
        result = await client.deleteComment(args.comment_id as string);
        break;

      // Label operations
      case "todoist_get_labels":
        result = await client.getLabels();
        break;

      case "todoist_create_label":
        result = await client.createLabel({
          name: args.name as string,
          color: args.color as string | undefined,
          is_favorite: args.is_favorite as boolean | undefined,
        });
        break;

      case "todoist_update_label":
        {
          const updates: any = {};
          if (args.name !== undefined) updates.name = args.name;
          if (args.color !== undefined) updates.color = args.color;
          if (args.is_favorite !== undefined) updates.is_favorite = args.is_favorite;

          result = await client.updateLabel(args.label_id as string, updates);
        }
        break;

      case "todoist_delete_label":
        result = await client.deleteLabel(args.label_id as string);
        break;

      default:
        throw new Error(`Unknown tool: ${name}`);
    }

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(result, null, 2),
        },
      ],
    };
  } catch (error) {
    return {
      content: [
        {
          type: "text",
          text: `Error: ${error instanceof Error ? error.message : String(error)}`,
        },
      ],
      isError: true,
    };
  }
});

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Todoist MCP Server running on stdio");
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
