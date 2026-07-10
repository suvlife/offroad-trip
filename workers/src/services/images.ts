/**
 * Image service — free / no-key. Returns picsum.photos placeholder URLs
 * seeded by the query so the same subject gets a stable image.
 * (Unsplash needed a key; dropped per the no-key requirement.)
 */

export function searchPhoto(query: string, seed = ""): string {
  const s = encodeURIComponent(seed || query || "offroad");
  return `https://picsum.photos/seed/${s}/800/600`;
}
