# Todoist MCP Server - Usage Examples

This document provides detailed examples of how to use the Todoist MCP server with Claude.

## Task Management

### Creating Tasks

**Basic Task:**
```
Create a task "Write documentation"
```

**Task with Description:**
```
Create a task "Implement feature X" with description "This feature should include authentication and error handling"
```

**Task with Due Date:**
```
Create a task "Submit report" due tomorrow at 5pm
```

**Task with Priority:**
```
Create a task "Fix critical bug" with priority 4 (urgent)
```

**Task with Labels:**
```
Create a task "Code review" with labels "development" and "urgent"
```

**Task in Specific Project:**
```
Create a task "Design mockups" in project [project_id]
```

**Subtask:**
```
Create a subtask "Review code changes" under task [parent_task_id]
```

### Viewing Tasks

**All Tasks:**
```
Show me all my tasks
```

**Today's Tasks:**
```
What tasks do I have today?
```

**Tasks by Priority:**
```
Show me all priority 4 tasks
```

**Tasks in a Project:**
```
List all tasks in project [project_id]
```

**Tasks with a Label:**
```
Show me all tasks with the "urgent" label
```

**Overdue Tasks:**
```
Show me my overdue tasks
```

### Updating Tasks

**Change Task Name:**
```
Rename task [task_id] to "Updated task name"
```

**Update Description:**
```
Update the description of task [task_id] to "New detailed description"
```

**Change Priority:**
```
Set task [task_id] to priority 3
```

**Update Due Date:**
```
Change the due date of task [task_id] to next Friday
```

**Add Labels:**
```
Add labels "important" and "work" to task [task_id]
```

### Completing and Managing Tasks

**Complete a Task:**
```
Mark task [task_id] as complete
```

**Reopen a Task:**
```
Reopen task [task_id]
```

**Delete a Task:**
```
Delete task [task_id]
```

## Project Management

### Creating Projects

**Basic Project:**
```
Create a project called "Website Redesign"
```

**Project with Color:**
```
Create a project "Marketing Campaign" with color "berry_red"
```

**Subproject:**
```
Create a subproject "Phase 1" under project [parent_project_id]
```

**Favorite Project:**
```
Create a favorite project called "Important Tasks"
```

**Board View Project:**
```
Create a project "Sprint Board" with board view style
```

### Managing Projects

**List All Projects:**
```
Show me all my projects
```

**Get Project Details:**
```
Show me details for project [project_id]
```

**Rename Project:**
```
Rename project [project_id] to "New Project Name"
```

**Change Project Color:**
```
Change the color of project [project_id] to "blue"
```

**Toggle Favorite:**
```
Make project [project_id] a favorite
```

**Delete Project:**
```
Delete project [project_id]
```

## Section Management

### Creating Sections

**Basic Section:**
```
Create a section "In Progress" in project [project_id]
```

**Multiple Sections:**
```
Create sections "To Do", "In Progress", and "Done" in project [project_id]
```

### Managing Sections

**List Sections:**
```
Show me all sections in project [project_id]
```

**Rename Section:**
```
Rename section [section_id] to "Completed Tasks"
```

**Delete Section:**
```
Delete section [section_id]
```

## Comments

### Adding Comments

**Comment on Task:**
```
Add comment "This looks good to me" to task [task_id]
```

**Comment on Project:**
```
Add comment "Project kickoff meeting scheduled for Monday" to project [project_id]
```

**Markdown Comment:**
```
Add this comment to task [task_id]:
"## Review Notes
- Code quality is excellent
- Tests pass
- Ready to merge"
```

### Managing Comments

**View Comments:**
```
Show me all comments on task [task_id]
```

**Update Comment:**
```
Update comment [comment_id] to "Revised feedback: approved"
```

**Delete Comment:**
```
Delete comment [comment_id]
```

## Labels

### Creating Labels

**Basic Label:**
```
Create a label called "urgent"
```

**Label with Color:**
```
Create a label "high-priority" with color "red"
```

**Favorite Label:**
```
Create a favorite label "important"
```

### Managing Labels

**List All Labels:**
```
Show me all my labels
```

**Rename Label:**
```
Rename label [label_id] to "super-urgent"
```

**Change Label Color:**
```
Change the color of label [label_id] to "green"
```

**Delete Label:**
```
Delete label [label_id]
```

## Advanced Workflows

### Daily Planning

```
1. Show me all tasks due today
2. Show me all overdue tasks
3. Create a task "Review daily goals" due today at 9am with priority 3
```

### Project Setup

```
1. Create a project "Q1 Marketing Campaign"
2. Create sections "Planning", "Execution", and "Review" in the new project
3. Create a task "Define campaign goals" in the Planning section
4. Create a label "q1-marketing" with color "purple"
```

### Weekly Review

```
1. Show me all completed tasks from last week
2. Show me all tasks with label "this-week"
3. Create a task "Weekly review and planning" due next Monday
```

### Team Collaboration

```
1. Create a project "Team Sprint 23"
2. Add comment "Sprint planning: 2 weeks starting next Monday" to the project
3. Create tasks from the sprint backlog
4. Add comments with updates and blockers to tasks
```

## Task Filter Syntax

The Todoist MCP server supports powerful filter queries:

**Date Filters:**
- `today` - Tasks due today
- `tomorrow` - Tasks due tomorrow
- `next week` - Tasks due next week
- `overdue` - Overdue tasks
- `no date` - Tasks without a due date

**Priority Filters:**
- `p1` - Priority 4 (urgent) tasks
- `p2` - Priority 3 (high) tasks
- `p3` - Priority 2 (medium) tasks
- `p4` - Priority 1 (normal) tasks

**Label Filters:**
- `@work` - Tasks with "work" label
- `@urgent` - Tasks with "urgent" label

**Project Filters:**
- `#project_name` - Tasks in specific project

**Combined Filters:**
```
Show me tasks with filter "today & p1" (today's urgent tasks)
Show me tasks with filter "@work & overdue" (overdue work tasks)
Show me tasks with filter "#marketing & p2" (high priority marketing tasks)
```

## Tips and Best Practices

1. **Use Natural Language**: Claude can understand natural date formats like "tomorrow at 3pm", "next Friday", "in 2 weeks"

2. **Priority Levels**: Use priority 4 for truly urgent tasks, priority 1 for normal tasks

3. **Labels for Organization**: Create labels for contexts (@work, @home) and categories (bug, feature, documentation)

4. **Projects for Goals**: Use projects to organize larger goals and initiatives

5. **Sections for Workflow**: Create sections like "To Do", "In Progress", "Done" to track task status

6. **Comments for Context**: Add comments to tasks and projects to provide context and updates

7. **Regular Reviews**: Use filters to review tasks regularly (today, overdue, this week)

## Common Patterns

### GTD (Getting Things Done)

```
Create projects: "Inbox", "Next Actions", "Waiting For", "Someday/Maybe"
Create labels: "@work", "@home", "@computer", "@phone", "@errands"
Filter tasks by context: "@work & today"
```

### Agile Sprint Management

```
Create project: "Sprint [number]"
Create sections: "Backlog", "To Do", "In Progress", "Review", "Done"
Create labels: "bug", "feature", "tech-debt"
Track progress with comments
```

### Personal Task Management

```
Create projects by life area: "Work", "Personal", "Health", "Learning"
Use priority for urgency
Use labels for energy level: "@high-energy", "@low-energy"
Review tasks daily with "today" filter
```
