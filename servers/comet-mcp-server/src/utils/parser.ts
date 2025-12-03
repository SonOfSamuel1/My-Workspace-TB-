/**
 * Utility functions for parsing and cleaning Comet responses
 */

/**
 * Clean and parse Comet's response text
 */
export function parseResponse(rawText: string): string {
  // Remove common UI elements and noise
  let cleaned = rawText
    .replace(/^.*?(Comet|Assistant|AI):/gim, '') // Remove assistant prefixes
    .replace(/\[.*?\]/g, '') // Remove button text like [Copy], [Share]
    .replace(/Loading\.\.\./g, '') // Remove loading indicators
    .replace(/Thinking\.\.\./g, '') // Remove thinking indicators
    .replace(/^\s*Type a message.*$/gm, '') // Remove input field placeholder
    .trim();

  // Remove duplicate whitespace
  cleaned = cleaned.replace(/\s+/g, ' ');

  // Remove empty lines
  cleaned = cleaned.split('\n')
    .filter(line => line.trim().length > 0)
    .join('\n');

  return cleaned;
}

/**
 * Extract the most recent response from conversation history
 */
export function extractLatestResponse(fullText: string): string {
  // Split by common response separators
  const parts = fullText.split(/(?:You:|User:|Human:)/gi);

  // Get the last part that looks like an assistant response
  for (let i = parts.length - 1; i >= 0; i--) {
    const part = parts[i].trim();
    if (part.length > 10 && !part.includes('Type a message')) {
      return parseResponse(part);
    }
  }

  // Fallback to full text if we can't find a clear response
  return parseResponse(fullText);
}

/**
 * Check if a response appears complete
 */
export function isResponseComplete(text: string): boolean {
  // Check for common indicators of incomplete responses
  const incompleteIndicators = [
    /\.\.\.$/, // Ends with ellipsis
    /Loading$/i,
    /Thinking$/i,
    /Processing$/i,
    /\[incomplete\]/i
  ];

  for (const indicator of incompleteIndicators) {
    if (indicator.test(text)) {
      return false;
    }
  }

  // Check for minimum viable response
  if (text.length < 10) {
    return false;
  }

  // Check for sentence-ending punctuation
  const hasEndPunctuation = /[.!?]$/.test(text.trim());

  return hasEndPunctuation || text.length > 100;
}

/**
 * Extract URLs from response text
 */
export function extractURLs(text: string): string[] {
  const urlRegex = /https?:\/\/[^\s<>"{}|\\^`\[\]]+/gi;
  const matches = text.match(urlRegex) || [];
  return [...new Set(matches)]; // Remove duplicates
}

/**
 * Extract code blocks from response
 */
export function extractCodeBlocks(text: string): Array<{ lang?: string; code: string }> {
  const codeBlocks: Array<{ lang?: string; code: string }> = [];

  // Match fenced code blocks with optional language
  const fencedRegex = /```(\w+)?\n([\s\S]*?)```/g;
  let match;

  while ((match = fencedRegex.exec(text)) !== null) {
    codeBlocks.push({
      lang: match[1] || undefined,
      code: match[2].trim()
    });
  }

  // Also match inline code if no fenced blocks found
  if (codeBlocks.length === 0) {
    const inlineRegex = /`([^`]+)`/g;
    while ((match = inlineRegex.exec(text)) !== null) {
      codeBlocks.push({
        code: match[1].trim()
      });
    }
  }

  return codeBlocks;
}

/**
 * Split a long prompt into chunks if needed
 */
export function splitPrompt(prompt: string, maxLength: number = 4000): string[] {
  if (prompt.length <= maxLength) {
    return [prompt];
  }

  const chunks: string[] = [];
  const sentences = prompt.match(/[^.!?]+[.!?]+/g) || [prompt];

  let currentChunk = '';

  for (const sentence of sentences) {
    if ((currentChunk + sentence).length > maxLength) {
      if (currentChunk) {
        chunks.push(currentChunk.trim());
        currentChunk = sentence;
      } else {
        // Single sentence is too long, split by words
        const words = sentence.split(' ');
        let wordChunk = '';
        for (const word of words) {
          if ((wordChunk + ' ' + word).length > maxLength) {
            chunks.push(wordChunk.trim());
            wordChunk = word;
          } else {
            wordChunk += (wordChunk ? ' ' : '') + word;
          }
        }
        if (wordChunk) {
          currentChunk = wordChunk;
        }
      }
    } else {
      currentChunk += sentence;
    }
  }

  if (currentChunk) {
    chunks.push(currentChunk.trim());
  }

  return chunks;
}