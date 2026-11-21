// Test fixture for the thumbnail renderer: a tiny red frame, one declared word.
export const THUMB_SIZE = { w: 64, h: 36 };
export const WORDS: Record<'a' | 'b', string[]> = { a: ['HI'], b: [] };
export const THUMBS: Record<'a' | 'b', () => string> = {
  a: () => '<rect width="64" height="36" fill="#ff0000"/>',
  b: () => '<rect width="64" height="36" fill="#0000ff"/>',
};
