// Wraps localStorage so every value is obfuscated (not plain, human-readable
// JSON) and tamper-evident: a checksum is stored alongside the ciphertext, so
// if someone hand-edits a value in DevTools (e.g. to escalate a role), the
// checksum no longer matches and the value is discarded instead of trusted.
//
// Caveat: this is client-side JS — anyone who reads the bundle can find the
// cipher key. It is not server-grade confidentiality. What it does provide is
// protection against casual tampering via the browser's storage inspector,
// which is the actual threat here. The backend must still authorise every
// request on its own; never trust a stored role as an access decision.

// Must stay byte-identical to the main Sahai app's SECRET — the cipher key is
// derived from it, so a different value here would make NHCX unable to decode
// a session written by Sahai (and vice versa) on a shared origin.
const SECRET = 'sahai-hms-storage-v1-6f2a9c31';
const FORMAT_VERSION = 'v1';

function fnv1aHash(str: string): string {
  let hash = 0x811c9dc5;
  for (let i = 0; i < str.length; i++) {
    hash ^= str.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(36);
}

function xorCipher(input: string, key: string): string {
  let out = '';
  for (let i = 0; i < input.length; i++) {
    out += String.fromCharCode(input.charCodeAt(i) ^ key.charCodeAt(i % key.length));
  }
  return out;
}

function toBase64(str: string): string {
  return btoa(unescape(encodeURIComponent(str)));
}

function fromBase64(b64: string): string {
  return decodeURIComponent(escape(atob(b64)));
}

export function secureSetItem(key: string, value: unknown): void {
  const plaintext = JSON.stringify(value);
  const checksum = fnv1aHash(plaintext);
  const cipher = toBase64(xorCipher(plaintext, SECRET + key));
  localStorage.setItem(key, `${FORMAT_VERSION}.${checksum}.${cipher}`);
}

export function secureGetItem<T = unknown>(key: string): T | null {
  const raw = localStorage.getItem(key);
  if (!raw) return null;

  const parts = raw.split('.');
  if (parts.length !== 3 || parts[0] !== FORMAT_VERSION) {
    // Plaintext value written before this wrapper existed, or a tampered /
    // foreign value — either way it is not trustworthy. Drop it.
    localStorage.removeItem(key);
    return null;
  }

  const [, checksum, cipher] = parts;
  try {
    const plaintext = xorCipher(fromBase64(cipher), SECRET + key);
    if (fnv1aHash(plaintext) !== checksum) {
      localStorage.removeItem(key);
      return null;
    }
    return JSON.parse(plaintext) as T;
  } catch {
    localStorage.removeItem(key);
    return null;
  }
}

export function secureRemoveItem(key: string): void {
  localStorage.removeItem(key);
}

export function clearAllStorage(): void {
  localStorage.clear();
}
