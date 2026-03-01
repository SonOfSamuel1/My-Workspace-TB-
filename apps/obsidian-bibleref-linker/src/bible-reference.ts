import { BIBLE_BOOKS, BookInfo } from "./constants";

export interface BibleReference {
  fullMatch: string;
  book: BookInfo;
  chapter: number;
  verseStart: number | null;
  verseEnd: number | null;
  startIndex: number;
  endIndex: number;
}

// Build a map from all name variants (canonical + abbreviations) to book info
const bookLookup = new Map<string, BookInfo>();
for (const book of BIBLE_BOOKS) {
  bookLookup.set(book.canonical.toLowerCase(), book);
  for (const abbr of book.abbreviations) {
    bookLookup.set(abbr.toLowerCase(), book);
  }
}

// Build regex: collect all names, sort longest first to prevent partial matches
function buildBookNamesPattern(): string {
  const allNames: string[] = [];
  for (const book of BIBLE_BOOKS) {
    allNames.push(book.canonical);
    allNames.push(...book.abbreviations);
  }
  // Sort longest first
  allNames.sort((a, b) => b.length - a.length);
  // Escape regex special chars and join
  return allNames.map((n) => n.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|");
}

const bookPattern = buildBookNamesPattern();

// Full reference pattern:
// (BookName) (chapter)(?::(verse)(?:-(endVerse))?)?
// The \.? after book name allows optional period (e.g. "Gen. 1:1")
const BIBLE_REF_REGEX = new RegExp(
  `(?:^|(?<=\\s|[(["'\\u201C]))` + // lookbehind: start of string, whitespace, or opening punctuation
    `(${bookPattern})\\.?` + // book name with optional period
    `\\s+` + // required whitespace
    `(\\d{1,3})` + // chapter number
    `(?:` +
    `:(\\d{1,3})` + // optional :verse
    `(?:-(\\d{1,3}))?` + // optional -endVerse
    `)?` +
    `(?=$|[\\s,;.!?)\\]"'\\u201D])`, // lookahead: end, whitespace, or closing punctuation
  "gi"
);

export function findReferences(text: string): BibleReference[] {
  const results: BibleReference[] = [];
  BIBLE_REF_REGEX.lastIndex = 0;

  let match: RegExpExecArray | null;
  while ((match = BIBLE_REF_REGEX.exec(text)) !== null) {
    const bookName = match[1];
    const book = bookLookup.get(bookName.toLowerCase());
    if (!book) continue;

    const chapter = parseInt(match[2], 10);
    const verseStart = match[3] ? parseInt(match[3], 10) : null;
    const verseEnd = match[4] ? parseInt(match[4], 10) : null;

    results.push({
      fullMatch: match[0],
      book,
      chapter,
      verseStart,
      verseEnd,
      startIndex: match.index,
      endIndex: match.index + match[0].length,
    });
  }

  return results;
}

export function buildBibleRefUrl(ref: BibleReference): string {
  const { book, chapter, verseStart } = ref;
  const slug = book.biblerefSlug;

  if (verseStart != null) {
    // e.g. https://www.bibleref.com/John/3/John-3-16.html
    return `https://www.bibleref.com/${slug}/${chapter}/${slug}-${chapter}-${verseStart}.html`;
  }
  // Chapter-only: e.g. https://www.bibleref.com/Psalms/23/Psalms-chapter-23.html
  return `https://www.bibleref.com/${slug}/${chapter}/${slug}-chapter-${chapter}.html`;
}

export function buildApiQuery(ref: BibleReference, translation: string): string {
  const { book, chapter, verseStart, verseEnd } = ref;
  const name = book.apiName;

  let query: string;
  if (verseStart != null && verseEnd != null) {
    query = `${name} ${chapter}:${verseStart}-${verseEnd}`;
  } else if (verseStart != null) {
    query = `${name} ${chapter}:${verseStart}`;
  } else {
    query = `${name} ${chapter}`;
  }

  return `https://bible-api.com/${encodeURIComponent(query)}?translation=${translation}`;
}

export function referenceToString(ref: BibleReference): string {
  const { book, chapter, verseStart, verseEnd } = ref;
  if (verseStart != null && verseEnd != null) {
    return `${book.canonical} ${chapter}:${verseStart}-${verseEnd}`;
  }
  if (verseStart != null) {
    return `${book.canonical} ${chapter}:${verseStart}`;
  }
  return `${book.canonical} ${chapter}`;
}
