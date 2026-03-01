export interface BookInfo {
  canonical: string;
  abbreviations: string[];
  biblerefSlug: string;
  apiName: string;
}

// All 66 books of the Bible with their metadata
export const BIBLE_BOOKS: BookInfo[] = [
  // Old Testament
  {
    canonical: "Genesis",
    abbreviations: ["Gen", "Ge", "Gn"],
    biblerefSlug: "Genesis",
    apiName: "Genesis",
  },
  {
    canonical: "Exodus",
    abbreviations: ["Exod", "Exo", "Ex"],
    biblerefSlug: "Exodus",
    apiName: "Exodus",
  },
  {
    canonical: "Leviticus",
    abbreviations: ["Lev", "Le", "Lv"],
    biblerefSlug: "Leviticus",
    apiName: "Leviticus",
  },
  {
    canonical: "Numbers",
    abbreviations: ["Num", "Nu", "Nm", "Nb"],
    biblerefSlug: "Numbers",
    apiName: "Numbers",
  },
  {
    canonical: "Deuteronomy",
    abbreviations: ["Deut", "Dt", "De"],
    biblerefSlug: "Deuteronomy",
    apiName: "Deuteronomy",
  },
  {
    canonical: "Joshua",
    abbreviations: ["Josh", "Jos", "Jsh"],
    biblerefSlug: "Joshua",
    apiName: "Joshua",
  },
  {
    canonical: "Judges",
    abbreviations: ["Judg", "Jdg", "Jg", "Jdgs"],
    biblerefSlug: "Judges",
    apiName: "Judges",
  },
  { canonical: "Ruth", abbreviations: ["Rth", "Ru"], biblerefSlug: "Ruth", apiName: "Ruth" },
  {
    canonical: "1 Samuel",
    abbreviations: ["1 Sam", "1Sam", "1Sa", "1S"],
    biblerefSlug: "1-Samuel",
    apiName: "1 Samuel",
  },
  {
    canonical: "2 Samuel",
    abbreviations: ["2 Sam", "2Sam", "2Sa", "2S"],
    biblerefSlug: "2-Samuel",
    apiName: "2 Samuel",
  },
  {
    canonical: "1 Kings",
    abbreviations: ["1 Kgs", "1Kgs", "1Ki", "1K"],
    biblerefSlug: "1-Kings",
    apiName: "1 Kings",
  },
  {
    canonical: "2 Kings",
    abbreviations: ["2 Kgs", "2Kgs", "2Ki", "2K"],
    biblerefSlug: "2-Kings",
    apiName: "2 Kings",
  },
  {
    canonical: "1 Chronicles",
    abbreviations: ["1 Chr", "1Chr", "1Ch"],
    biblerefSlug: "1-Chronicles",
    apiName: "1 Chronicles",
  },
  {
    canonical: "2 Chronicles",
    abbreviations: ["2 Chr", "2Chr", "2Ch"],
    biblerefSlug: "2-Chronicles",
    apiName: "2 Chronicles",
  },
  { canonical: "Ezra", abbreviations: ["Ezr"], biblerefSlug: "Ezra", apiName: "Ezra" },
  {
    canonical: "Nehemiah",
    abbreviations: ["Neh", "Ne"],
    biblerefSlug: "Nehemiah",
    apiName: "Nehemiah",
  },
  {
    canonical: "Esther",
    abbreviations: ["Est", "Esth", "Es"],
    biblerefSlug: "Esther",
    apiName: "Esther",
  },
  { canonical: "Job", abbreviations: ["Jb"], biblerefSlug: "Job", apiName: "Job" },
  {
    canonical: "Psalms",
    abbreviations: ["Ps", "Psa", "Psm", "Pss", "Psalm"],
    biblerefSlug: "Psalms",
    apiName: "Psalms",
  },
  {
    canonical: "Proverbs",
    abbreviations: ["Prov", "Pro", "Prv", "Pr"],
    biblerefSlug: "Proverbs",
    apiName: "Proverbs",
  },
  {
    canonical: "Ecclesiastes",
    abbreviations: ["Eccl", "Ecc", "Ec", "Eccles"],
    biblerefSlug: "Ecclesiastes",
    apiName: "Ecclesiastes",
  },
  {
    canonical: "Song of Solomon",
    abbreviations: ["Song", "SOS", "So", "Song of Songs", "Songs"],
    biblerefSlug: "Song-of-Solomon",
    apiName: "Song of Solomon",
  },
  { canonical: "Isaiah", abbreviations: ["Isa", "Is"], biblerefSlug: "Isaiah", apiName: "Isaiah" },
  {
    canonical: "Jeremiah",
    abbreviations: ["Jer", "Je", "Jr"],
    biblerefSlug: "Jeremiah",
    apiName: "Jeremiah",
  },
  {
    canonical: "Lamentations",
    abbreviations: ["Lam", "La"],
    biblerefSlug: "Lamentations",
    apiName: "Lamentations",
  },
  {
    canonical: "Ezekiel",
    abbreviations: ["Ezek", "Eze", "Ezk"],
    biblerefSlug: "Ezekiel",
    apiName: "Ezekiel",
  },
  {
    canonical: "Daniel",
    abbreviations: ["Dan", "Da", "Dn"],
    biblerefSlug: "Daniel",
    apiName: "Daniel",
  },
  { canonical: "Hosea", abbreviations: ["Hos", "Ho"], biblerefSlug: "Hosea", apiName: "Hosea" },
  { canonical: "Joel", abbreviations: ["Jl", "Joe"], biblerefSlug: "Joel", apiName: "Joel" },
  { canonical: "Amos", abbreviations: ["Am"], biblerefSlug: "Amos", apiName: "Amos" },
  {
    canonical: "Obadiah",
    abbreviations: ["Obad", "Ob"],
    biblerefSlug: "Obadiah",
    apiName: "Obadiah",
  },
  { canonical: "Jonah", abbreviations: ["Jon", "Jnh"], biblerefSlug: "Jonah", apiName: "Jonah" },
  { canonical: "Micah", abbreviations: ["Mic", "Mc"], biblerefSlug: "Micah", apiName: "Micah" },
  { canonical: "Nahum", abbreviations: ["Nah", "Na"], biblerefSlug: "Nahum", apiName: "Nahum" },
  {
    canonical: "Habakkuk",
    abbreviations: ["Hab", "Hb"],
    biblerefSlug: "Habakkuk",
    apiName: "Habakkuk",
  },
  {
    canonical: "Zephaniah",
    abbreviations: ["Zeph", "Zep", "Zp"],
    biblerefSlug: "Zephaniah",
    apiName: "Zephaniah",
  },
  { canonical: "Haggai", abbreviations: ["Hag", "Hg"], biblerefSlug: "Haggai", apiName: "Haggai" },
  {
    canonical: "Zechariah",
    abbreviations: ["Zech", "Zec", "Zc"],
    biblerefSlug: "Zechariah",
    apiName: "Zechariah",
  },
  {
    canonical: "Malachi",
    abbreviations: ["Mal", "Ml"],
    biblerefSlug: "Malachi",
    apiName: "Malachi",
  },

  // New Testament
  {
    canonical: "Matthew",
    abbreviations: ["Matt", "Mat", "Mt"],
    biblerefSlug: "Matthew",
    apiName: "Matthew",
  },
  { canonical: "Mark", abbreviations: ["Mrk", "Mk", "Mr"], biblerefSlug: "Mark", apiName: "Mark" },
  { canonical: "Luke", abbreviations: ["Luk", "Lk"], biblerefSlug: "Luke", apiName: "Luke" },
  { canonical: "John", abbreviations: ["Jhn", "Jn"], biblerefSlug: "John", apiName: "John" },
  { canonical: "Acts", abbreviations: ["Act", "Ac"], biblerefSlug: "Acts", apiName: "Acts" },
  {
    canonical: "Romans",
    abbreviations: ["Rom", "Ro", "Rm"],
    biblerefSlug: "Romans",
    apiName: "Romans",
  },
  {
    canonical: "1 Corinthians",
    abbreviations: ["1 Cor", "1Cor", "1Co"],
    biblerefSlug: "1-Corinthians",
    apiName: "1 Corinthians",
  },
  {
    canonical: "2 Corinthians",
    abbreviations: ["2 Cor", "2Cor", "2Co"],
    biblerefSlug: "2-Corinthians",
    apiName: "2 Corinthians",
  },
  {
    canonical: "Galatians",
    abbreviations: ["Gal", "Ga"],
    biblerefSlug: "Galatians",
    apiName: "Galatians",
  },
  {
    canonical: "Ephesians",
    abbreviations: ["Eph", "Ep"],
    biblerefSlug: "Ephesians",
    apiName: "Ephesians",
  },
  {
    canonical: "Philippians",
    abbreviations: ["Phil", "Php", "Pp"],
    biblerefSlug: "Philippians",
    apiName: "Philippians",
  },
  {
    canonical: "Colossians",
    abbreviations: ["Col", "Co"],
    biblerefSlug: "Colossians",
    apiName: "Colossians",
  },
  {
    canonical: "1 Thessalonians",
    abbreviations: ["1 Thess", "1Thess", "1Th", "1Thes"],
    biblerefSlug: "1-Thessalonians",
    apiName: "1 Thessalonians",
  },
  {
    canonical: "2 Thessalonians",
    abbreviations: ["2 Thess", "2Thess", "2Th", "2Thes"],
    biblerefSlug: "2-Thessalonians",
    apiName: "2 Thessalonians",
  },
  {
    canonical: "1 Timothy",
    abbreviations: ["1 Tim", "1Tim", "1Ti"],
    biblerefSlug: "1-Timothy",
    apiName: "1 Timothy",
  },
  {
    canonical: "2 Timothy",
    abbreviations: ["2 Tim", "2Tim", "2Ti"],
    biblerefSlug: "2-Timothy",
    apiName: "2 Timothy",
  },
  { canonical: "Titus", abbreviations: ["Tit", "Ti"], biblerefSlug: "Titus", apiName: "Titus" },
  {
    canonical: "Philemon",
    abbreviations: ["Phlm", "Phm", "Philem"],
    biblerefSlug: "Philemon",
    apiName: "Philemon",
  },
  { canonical: "Hebrews", abbreviations: ["Heb"], biblerefSlug: "Hebrews", apiName: "Hebrews" },
  { canonical: "James", abbreviations: ["Jas", "Jm"], biblerefSlug: "James", apiName: "James" },
  {
    canonical: "1 Peter",
    abbreviations: ["1 Pet", "1Pet", "1Pt", "1Pe"],
    biblerefSlug: "1-Peter",
    apiName: "1 Peter",
  },
  {
    canonical: "2 Peter",
    abbreviations: ["2 Pet", "2Pet", "2Pt", "2Pe"],
    biblerefSlug: "2-Peter",
    apiName: "2 Peter",
  },
  {
    canonical: "1 John",
    abbreviations: ["1 Jn", "1Jn", "1Jhn", "1Jo"],
    biblerefSlug: "1-John",
    apiName: "1 John",
  },
  {
    canonical: "2 John",
    abbreviations: ["2 Jn", "2Jn", "2Jhn", "2Jo"],
    biblerefSlug: "2-John",
    apiName: "2 John",
  },
  {
    canonical: "3 John",
    abbreviations: ["3 Jn", "3Jn", "3Jhn", "3Jo"],
    biblerefSlug: "3-John",
    apiName: "3 John",
  },
  { canonical: "Jude", abbreviations: ["Jud", "Jde"], biblerefSlug: "Jude", apiName: "Jude" },
  {
    canonical: "Revelation",
    abbreviations: ["Rev", "Re", "Rv"],
    biblerefSlug: "Revelation",
    apiName: "Revelation",
  },
];

export const TRANSLATIONS = [
  { value: "web", label: "WEB (World English Bible)" },
  { value: "kjv", label: "KJV (King James Version)" },
  { value: "asv", label: "ASV (American Standard Version)" },
  { value: "bbe", label: "BBE (Bible in Basic English)" },
  { value: "darby", label: "Darby Translation" },
  { value: "ylt", label: "YLT (Young's Literal Translation)" },
];

export const DEFAULT_SETTINGS = {
  autoLink: true,
  translation: "web",
  openInBrowser: true,
  showPopover: true,
};
