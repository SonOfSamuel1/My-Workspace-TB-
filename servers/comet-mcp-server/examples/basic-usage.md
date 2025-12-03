# Comet MCP Server - Basic Usage Examples

## Getting Started

After building the server and registering it in `.claude/mcp.json`, you can use Claude Code to interact with Comet browser.

## Example Commands for Claude Code

### 1. Simple Research Query

Ask Claude:
```
Use Comet to research "quantum computing breakthroughs in 2024"
```

Claude will:
- Activate Comet browser
- Send the research prompt
- Wait for and return the response

### 2. Web Navigation and Summary

Ask Claude:
```
Navigate to https://news.ycombinator.com in Comet and summarize the top stories
```

Claude will:
- Navigate to the URL
- Extract page content
- Send a summarization prompt
- Return the summary

### 3. Multi-Step Research

Ask Claude:
```
Use Comet to:
1. Research "renewable energy technologies"
2. Ask about solar panel efficiency improvements
3. Ask about wind turbine innovations
4. Take a screenshot of the results
```

### 4. Batch Processing

Ask Claude:
```
Send these questions to Comet in sequence:
- What is machine learning?
- How do neural networks work?
- What are the applications of AI in healthcare?
```

## Direct Tool Usage (for developers)

If you're developing with the MCP SDK, you can call tools directly:

```javascript
// Send a single prompt
await mcp.callTool('comet_send_prompt', {
  prompt: 'What is the meaning of life?',
  wait_for_response: true
});

// Navigate and extract
await mcp.callTool('comet_navigate', {
  url: 'https://example.com'
});

const content = await mcp.callTool('comet_extract_page', {});

// Research with follow-ups
await mcp.callTool('comet_research_topic', {
  topic: 'artificial intelligence',
  follow_up_questions: [
    'What are the ethical considerations?',
    'How is it being regulated?'
  ]
});
```

## Troubleshooting Tips

### If Comet doesn't respond:
1. Ensure Comet is running (`comet_health_check`)
2. Check Accessibility permissions
3. Try `comet_clear` to reset the conversation

### For better results:
1. Be specific in your prompts
2. Allow time for responses to complete
3. Use follow-up questions for deeper research
4. Take screenshots for visual reference

## Advanced Workflows

### Research and Documentation
```
1. Research a topic in Comet
2. Extract key points
3. Generate a summary
4. Save to a file
5. Create a task in your todo app
```

### Competitive Analysis
```
1. Navigate to competitor websites
2. Extract product information
3. Ask Comet to compare features
4. Generate a comparison table
```

### Learning Assistant
```
1. Ask Comet to explain a concept
2. Request examples
3. Ask for practice problems
4. Get solutions and explanations
```

## Integration with Other MCP Servers

Combine Comet with other MCP servers in your workflow:

```
# Research with Comet → Save to Todoist
1. Use Comet to research project requirements
2. Extract action items from the research
3. Create tasks in Todoist with the extracted items

# Web Content → Email Summary
1. Navigate to news sites with Comet
2. Extract and summarize content
3. Send summary via Gmail MCP server
```

## Best Practices

1. **Start Simple**: Test with basic prompts first
2. **Be Patient**: Allow responses to complete fully
3. **Clear Context**: Use `comet_clear` between unrelated tasks
4. **Save Progress**: Take screenshots of important responses
5. **Verify Health**: Check browser status regularly

## Common Use Cases

- **Research**: Academic papers, technical documentation, market analysis
- **Learning**: Tutorials, explanations, problem-solving
- **Content Creation**: Article research, fact-checking, idea generation
- **Analysis**: Competitive analysis, trend research, data interpretation
- **Automation**: Repetitive queries, batch processing, scheduled research

## Error Recovery

If something goes wrong:

1. Check if Comet is still running
2. Try clearing the conversation
3. Restart Comet if needed
4. Verify Accessibility permissions
5. Check the server logs for detailed errors

Remember: The Comet MCP server uses desktop automation, so keep Comet visible and avoid switching windows during operations.