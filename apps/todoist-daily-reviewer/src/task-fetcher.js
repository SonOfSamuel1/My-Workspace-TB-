/**
 * Task Fetcher - Fetches and aggregates tasks from Todoist API
 *
 * This module handles all Todoist API interactions for the daily reviewer.
 */

const TODOIST_API_BASE = 'https://api.todoist.com/rest/v2';

/**
 * Todoist API Client
 */
class TodoistClient {
  constructor(apiToken) {
    if (!apiToken) {
      throw new Error('TODOIST_API_TOKEN is required');
    }
    this.apiToken = apiToken;
  }

  /**
   * Make authenticated request to Todoist API
   */
  async makeRequest(endpoint, method = 'GET', body = null) {
    const url = `${TODOIST_API_BASE}${endpoint}`;
    const headers = {
      'Authorization': `Bearer ${this.apiToken}`,
      'Content-Type': 'application/json'
    };

    const options = { method, headers };

    if (body && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
      options.body = JSON.stringify(body);
    }

    const response = await fetch(url, options);

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Todoist API error (${response.status}): ${errorText}`);
    }

    if (method === 'DELETE' && response.status === 204) {
      return { success: true };
    }

    return response.json();
  }

  /**
   * Get tasks with optional filters
   */
  async getTasks(params = {}) {
    let endpoint = '/tasks';
    const queryParams = new URLSearchParams();

    if (params.project_id) queryParams.append('project_id', params.project_id);
    if (params.section_id) queryParams.append('section_id', params.section_id);
    if (params.label) queryParams.append('label', params.label);
    if (params.filter) queryParams.append('filter', params.filter);
    if (params.ids) queryParams.append('ids', params.ids.join(','));

    const queryString = queryParams.toString();
    if (queryString) endpoint += `?${queryString}`;

    return this.makeRequest(endpoint);
  }

  /**
   * Get all projects
   */
  async getProjects() {
    return this.makeRequest('/projects');
  }

  /**
   * Get all labels
   */
  async getLabels() {
    return this.makeRequest('/labels');
  }

  /**
   * Get task comments
   */
  async getComments(taskId) {
    return this.makeRequest(`/comments?task_id=${taskId}`);
  }
}

/**
 * Task Fetcher - Aggregates and processes tasks for daily review
 */
export class TaskFetcher {
  constructor(apiToken, config = {}) {
    this.client = new TodoistClient(apiToken);
    this.config = config;
  }

  /**
   * Fetch all high-priority tasks for review
   */
  async fetchTasksForReview() {
    const results = {
      highPriority: [],
      overdue: [],
      dueToday: [],
      upcoming: [],
      all: [],
      metadata: {
        fetchedAt: new Date().toISOString(),
        filters: this.config.filters || {}
      }
    };

    try {
      // Fetch tasks by different criteria in parallel
      const [
        urgentTasks,
        highPriorityTasks,
        mediumPriorityTasks,
        overdueTasks,
        todayTasks,
        weekTasks,
        projects,
        labels
      ] = await Promise.all([
        this.client.getTasks({ filter: 'p1' }),  // Urgent (priority 4)
        this.client.getTasks({ filter: 'p2' }),  // High (priority 3)
        this.client.getTasks({ filter: 'p3' }),  // Medium (priority 2)
        this.client.getTasks({ filter: 'overdue' }),
        this.client.getTasks({ filter: 'today' }),
        this.client.getTasks({ filter: '7 days' }),
        this.client.getProjects(),
        this.client.getLabels()
      ]);

      // Create lookup maps
      const projectMap = new Map(projects.map(p => [p.id, p]));
      const labelMap = new Map(labels.map(l => [l.name, l]));

      // Combine all tasks and deduplicate
      const allTasks = new Map();

      const addTasks = (tasks, category) => {
        for (const task of tasks) {
          if (!allTasks.has(task.id)) {
            // Enrich task with project info
            const enrichedTask = this.enrichTask(task, projectMap, labelMap);
            enrichedTask.categories = [category];
            allTasks.set(task.id, enrichedTask);
          } else {
            // Add category to existing task
            allTasks.get(task.id).categories.push(category);
          }
        }
      };

      addTasks(urgentTasks, 'urgent');
      addTasks(highPriorityTasks, 'high');
      addTasks(mediumPriorityTasks, 'medium');
      addTasks(overdueTasks, 'overdue');
      addTasks(todayTasks, 'today');
      addTasks(weekTasks, 'upcoming');

      // Filter out excluded labels
      const excludeLabels = this.config.filters?.excludeLabels || [];
      const filteredTasks = Array.from(allTasks.values()).filter(task => {
        if (!task.labels || task.labels.length === 0) return true;
        return !task.labels.some(label => excludeLabels.includes(label));
      });

      // Sort by priority and due date
      const sortedTasks = filteredTasks.sort((a, b) => {
        // Priority first (higher number = more urgent in Todoist)
        if (b.priority !== a.priority) {
          return b.priority - a.priority;
        }
        // Then by due date
        if (a.due?.date && b.due?.date) {
          return new Date(a.due.date) - new Date(b.due.date);
        }
        if (a.due?.date) return -1;
        if (b.due?.date) return 1;
        return 0;
      });

      // Categorize results
      for (const task of sortedTasks) {
        results.all.push(task);

        if (task.categories.includes('urgent') || task.categories.includes('high')) {
          results.highPriority.push(task);
        }
        if (task.categories.includes('overdue')) {
          results.overdue.push(task);
        }
        if (task.categories.includes('today')) {
          results.dueToday.push(task);
        }
        if (task.categories.includes('upcoming') && !task.categories.includes('today')) {
          results.upcoming.push(task);
        }
      }

      // Add summary metadata
      results.metadata.summary = {
        total: results.all.length,
        highPriority: results.highPriority.length,
        overdue: results.overdue.length,
        dueToday: results.dueToday.length,
        upcoming: results.upcoming.length
      };

      results.metadata.projects = projects;
      results.metadata.labels = labels;

      return results;

    } catch (error) {
      console.error('Error fetching tasks:', error);
      throw error;
    }
  }

  /**
   * Enrich task with project and label details
   */
  enrichTask(task, projectMap, labelMap) {
    const enriched = { ...task };

    // Add project details
    if (task.project_id && projectMap.has(task.project_id)) {
      enriched.project = projectMap.get(task.project_id);
    }

    // Calculate days until due / days overdue
    if (task.due?.date) {
      const dueDate = new Date(task.due.date);
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      dueDate.setHours(0, 0, 0, 0);

      const diffTime = dueDate - today;
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

      enriched.daysUntilDue = diffDays;
      enriched.isOverdue = diffDays < 0;
      enriched.isDueToday = diffDays === 0;
    }

    // Add human-readable priority
    const priorityLabels = {
      4: 'Urgent',
      3: 'High',
      2: 'Medium',
      1: 'Low'
    };
    enriched.priorityLabel = priorityLabels[task.priority] || 'Normal';

    return enriched;
  }

  /**
   * Get a formatted summary of tasks
   */
  getTaskSummary(tasks) {
    return {
      totalTasks: tasks.all.length,
      byPriority: {
        urgent: tasks.all.filter(t => t.priority === 4).length,
        high: tasks.all.filter(t => t.priority === 3).length,
        medium: tasks.all.filter(t => t.priority === 2).length,
        low: tasks.all.filter(t => t.priority === 1).length
      },
      byStatus: {
        overdue: tasks.overdue.length,
        dueToday: tasks.dueToday.length,
        upcoming: tasks.upcoming.length
      },
      byProject: this.groupByProject(tasks.all)
    };
  }

  /**
   * Group tasks by project
   */
  groupByProject(tasks) {
    const grouped = {};
    for (const task of tasks) {
      const projectName = task.project?.name || 'Inbox';
      if (!grouped[projectName]) {
        grouped[projectName] = [];
      }
      grouped[projectName].push(task);
    }
    return grouped;
  }
}

export default TaskFetcher;
