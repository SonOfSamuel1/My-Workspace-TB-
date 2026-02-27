import { requestUrl } from "obsidian";
import { BibleReference, buildApiQuery, referenceToString } from "./bible-reference";
import { VerseCache, CacheEntry } from "./verse-cache";

export interface VerseResult {
  text: string;
  reference: string;
  translation: string;
  error?: string;
}

export class VerseApi {
  private cache: VerseCache;

  constructor(cache: VerseCache) {
    this.cache = cache;
  }

  async fetchVerse(ref: BibleReference, translation: string): Promise<VerseResult> {
    const cacheKey = `${referenceToString(ref)}:${translation}`;

    const cached = this.cache.get(cacheKey);
    if (cached) {
      return {
        text: cached.text,
        reference: cached.reference,
        translation: cached.translation,
      };
    }

    try {
      const url = buildApiQuery(ref, translation);
      const response = await requestUrl({ url, method: "GET" });
      const data = response.json;

      if (data.error) {
        return {
          text: "",
          reference: referenceToString(ref),
          translation,
          error: data.error,
        };
      }

      const verseText = (data.text || "").trim();
      const refName = data.reference || referenceToString(ref);
      const transName = data.translation_name || translation.toUpperCase();

      this.cache.set(cacheKey, {
        text: verseText,
        reference: refName,
        translation: transName,
        timestamp: Date.now(),
      });

      return {
        text: verseText,
        reference: refName,
        translation: transName,
      };
    } catch (err) {
      return {
        text: "",
        reference: referenceToString(ref),
        translation,
        error: err instanceof Error ? err.message : "Failed to fetch verse",
      };
    }
  }
}
