# Documentation Directory

Centralized documentation, guides, and reference materials for the workspace.

## Available Documentation

### Technical Guides

**mcp-server-configurator.md**
- MCP server configuration guide
- Setup instructions for Claude Code and Claude Desktop
- Troubleshooting common configuration issues

**YNAB_MCP_TROUBLESHOOTING.md**
- YNAB MCP server troubleshooting guide
- Common errors and solutions
- Configuration validation steps

### Financial Documentation

**Active_Offers_LLC_Self_Employment_Ledger.md**
- Self-employment financial ledger
- Income and expense tracking
- Business documentation

**Active_Offers_LLC_Self_Employment_Ledger.pdf**
- PDF version of financial ledger
- Formatted for printing and archival

### Research and Reference

**perplexity-research.md**
- Research notes and findings
- Reference material
- Investigation documentation

## Documentation Structure

### Organizational Principles

Documentation in this directory follows these principles:

1. **Centralized Reference**
   - Workspace-level documentation
   - Cross-project guides
   - Shared reference materials

2. **Discoverability**
   - Clear, descriptive filenames
   - Organized by topic
   - Referenced from project READMEs

3. **Accessibility**
   - Written in Markdown for readability
   - Includes examples and code snippets
   - Provides step-by-step instructions

## Document Types

### Setup Guides
Step-by-step instructions for configuring systems, services, or tools.

**Structure:**
- Prerequisites
- Installation steps
- Configuration
- Verification
- Troubleshooting

**Example:** mcp-server-configurator.md

### Troubleshooting Guides
Problem-solution documentation for common issues.

**Structure:**
- Issue description
- Symptoms
- Root cause
- Solution steps
- Prevention tips

**Example:** YNAB_MCP_TROUBLESHOOTING.md

### Reference Documentation
Technical reference materials, API docs, specifications.

**Structure:**
- Overview
- Detailed specifications
- Examples
- Related resources

### Research Notes
Investigation findings, research results, learning documentation.

**Structure:**
- Research question
- Findings
- Sources
- Conclusions
- Next steps

**Example:** perplexity-research.md

### Financial Documentation
Business records, ledgers, financial tracking.

**Structure:**
- Time period
- Transactions
- Summaries
- Supporting documentation

**Example:** Active_Offers_LLC_Self_Employment_Ledger.md

## Adding Documentation

### When to Add Docs Here

Add documentation to this directory when it:
- Applies to multiple projects
- Provides workspace-wide guidance
- Serves as shared reference material
- Contains business/financial records
- Documents cross-cutting concerns

### When to Keep Docs in Projects

Keep documentation in project directories when it:
- Is specific to that project
- Contains project setup instructions
- Documents project-specific APIs
- Explains project architecture

**Example:**
- `apps/love-brittany-tracker/docs/` - Love Brittany specific guides
- `docs/` - Workspace-wide MCP configuration

### Creating New Documentation

1. **Choose appropriate format:**
   - Markdown (.md) for most documentation
   - PDF for archival or formatted documents
   - TXT for simple reference files

2. **Use descriptive filenames:**
   - ALL_CAPS for important documents
   - kebab-case or snake_case for readability
   - Include version or date if applicable

3. **Include metadata:**
   ```markdown
   # Document Title

   **Author:** Your Name
   **Created:** YYYY-MM-DD
   **Last Updated:** YYYY-MM-DD
   **Version:** 1.0

   ## Purpose
   Brief description of document purpose...
   ```

4. **Add table of contents for long docs:**
   ```markdown
   ## Table of Contents
   - [Section 1](#section-1)
   - [Section 2](#section-2)
   - [Section 3](#section-3)
   ```

5. **Link from relevant locations:**
   - Reference from project READMEs
   - Add to workspace CLAUDE.md if significant
   - Cross-reference related docs

## Documentation Standards

### Writing Style

**Be Clear and Concise:**
- Use simple, direct language
- Avoid jargon unless necessary
- Define technical terms
- Use active voice

**Be Specific:**
- Include exact commands
- Provide concrete examples
- Show expected output
- Specify versions when relevant

**Be Complete:**
- Cover prerequisites
- Include all steps
- Provide alternatives when available
- Document edge cases

### Code Examples

**Format code blocks:**
```markdown
\```bash
npm install
npm run build
\```
```

**Include context:**
```markdown
Run the following command to install dependencies:
\```bash
npm install
\```

This will install all packages listed in package.json.
```

**Show output:**
```markdown
\```bash
$ npm run build
> Building project...
> Build successful!
\```
```

### File Paths

**Use absolute paths in examples:**
```bash
# Good
cd /Users/terrancebrandon/Desktop/Code\ Projects\ \(Official\)/My\ Workspace

# Avoid (ambiguous)
cd ~/Workspace
```

**Or relative from known location:**
```bash
# From workspace root
cd apps/love-brittany-tracker
```

### Command Examples

**Show the command and context:**
```bash
# Navigate to project directory
cd servers/todoist-mcp-server

# Install dependencies
npm install

# Build the server
npm run build
```

**Include expected output for verification:**
```bash
$ npm run build
> todoist-mcp-server@1.0.0 build
> tsc
# Successful build produces no output
```

## Maintenance

### Review Schedule

**Quarterly Review:**
- Verify accuracy of technical guides
- Update outdated information
- Remove obsolete documentation
- Add new documentation as needed

**After Major Changes:**
- Update affected documentation immediately
- Verify all links still work
- Update version numbers
- Add migration guides if needed

### Version Control

For documents that change frequently:
- Include version number in filename or header
- Maintain changelog section
- Archive old versions if needed
- Document breaking changes

Example:
```markdown
# MCP Server Configuration Guide

**Version:** 2.0
**Last Updated:** 2025-11-16

## Changelog

### Version 2.0 (2025-11-16)
- Added support for new MCP protocol version
- Updated configuration format
- Migrated from .claude to .mcp.json

### Version 1.0 (2025-10-01)
- Initial version
```

## Organization

### Current Organization

```
docs/
├── CLAUDE.md                                      # This file
├── Active_Offers_LLC_Self_Employment_Ledger.md   # Financial records
├── Active_Offers_LLC_Self_Employment_Ledger.pdf  # Financial records (PDF)
├── mcp-server-configurator.md                    # MCP setup guide
├── perplexity-research.md                        # Research notes
└── YNAB_MCP_TROUBLESHOOTING.md                  # YNAB troubleshooting
```

### Future Organization

As documentation grows, consider organizing into subdirectories:

```
docs/
├── CLAUDE.md                  # This file
├── technical/                 # Technical guides and references
│   ├── mcp-server-configurator.md
│   └── YNAB_MCP_TROUBLESHOOTING.md
├── financial/                 # Financial records and documentation
│   ├── Active_Offers_LLC_Self_Employment_Ledger.md
│   └── Active_Offers_LLC_Self_Employment_Ledger.pdf
├── research/                  # Research and investigation notes
│   └── perplexity-research.md
└── templates/                 # Document templates
    └── project-readme-template.md
```

## Cross-References

### Internal Links

Link to other workspace documentation:
```markdown
See also:
- [Workspace Overview](../CLAUDE.md)
- [Applications](../apps/CLAUDE.md)
- [MCP Servers](../servers/CLAUDE.md)
- [Utilities](../utils/CLAUDE.md)
```

### Project Documentation

Link to project-specific docs:
```markdown
For Love Brittany specific setup:
- [Love Brittany Quick Start](../apps/love-brittany-tracker/docs/QUICK_START_RELATIONSHIP.md)
- [Relationship Setup Guide](../apps/love-brittany-tracker/docs/RELATIONSHIP_SETUP_GUIDE.md)
```

## Resources

### Markdown References
- [Markdown Guide](https://www.markdownguide.org/)
- [GitHub Flavored Markdown](https://github.github.com/gfm/)

### Documentation Best Practices
- [Write the Docs](https://www.writethedocs.org/)
- [Google Developer Documentation Style Guide](https://developers.google.com/style)

### Tools
- [Markdown Preview](https://markdownlivepreview.com/) - Preview Markdown online
- [Mermaid](https://mermaid.js.org/) - Diagrams in Markdown
- [Shields.io](https://shields.io/) - Badges for documentation

### Related Directories
- [Main Workspace](../CLAUDE.md)
- [Applications](../apps/CLAUDE.md)
- [MCP Servers](../servers/CLAUDE.md)
- [Utilities](../utils/CLAUDE.md)

---

**Directory Purpose:** Centralized documentation and reference materials
**Last Updated:** 2025-11-16
