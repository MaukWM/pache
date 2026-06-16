const API_BASE = '/api/v1';

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem('token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options?.headers as Record<string, string>) || {}),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail || res.statusText);
  }

  return res.json();
}

async function requestNoBody(path: string, options?: RequestInit): Promise<void> {
  const token = localStorage.getItem('token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options?.headers as Record<string, string>) || {}),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail || res.statusText);
  }
}

// Auth
export interface User {
  id: number;
  username: string;
  is_admin?: boolean;
}

export interface CreatedUser extends User {
  password: string;
}

export interface LoginResponse {
  token: string;
  user: User;
}

export interface SettingsResponse {
  wk_api_key_configured: boolean;
  password_set: boolean;
}

export interface ImportResponse {
  imported_count: number;
  skipped_count: number;
  already_existed: number;
  total_fetched: number;
}

export interface WanikaniStatus {
  configured: boolean;
  reviews_due: number | null;
}

export const api = {
  login: (username: string, password: string) =>
    request<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),

  setPassword: (new_password: string) =>
    request<SettingsResponse>('/auth/password', {
      method: 'POST',
      body: JSON.stringify({ new_password }),
    }),

  // Admin user management
  listUsers: () => request<User[]>('/auth/users'),

  createUser: (username: string, password?: string, is_admin = false) =>
    request<CreatedUser>('/auth/users', {
      method: 'POST',
      body: JSON.stringify({ username, password: password || null, is_admin }),
    }),

  resetUserPassword: (userId: number, new_password?: string) =>
    request<CreatedUser>(`/auth/users/${userId}/password`, {
      method: 'POST',
      body: JSON.stringify({ new_password: new_password || null }),
    }),

  setUserAdmin: (userId: number, is_admin: boolean) =>
    request<User>(`/auth/users/${userId}/admin`, {
      method: 'POST',
      body: JSON.stringify({ is_admin }),
    }),

  // Settings
  getSettings: () =>
    request<SettingsResponse>('/auth/settings'),

  updateSettings: (wk_api_key: string) =>
    request<SettingsResponse>('/auth/settings', {
      method: 'POST',
      body: JSON.stringify({ wk_api_key }),
    }),

  removeSettings: () =>
    request<SettingsResponse>('/auth/settings', {
      method: 'POST',
      body: JSON.stringify({ wk_api_key: null }),
    }),

  // WaniKani import
  importWanikani: () =>
    request<ImportResponse>('/me/import/wanikani', { method: 'POST' }),

  // WaniKani live review status
  getWanikaniStatus: () =>
    request<WanikaniStatus>('/me/wanikani/status'),

  // Reviews
  getReviews: async (): Promise<ReviewItem[]> => {
    const res = await request<{ items: ReviewItem[]; count: number }>('/me/reviews');
    return res.items;
  },

  submitReview: (data: {
    item_type: string;
    item_id: number;
    reading_correct: boolean;
    meaning_correct: boolean;
  }) =>
    request<{
      srs_stage_before: number;
      srs_stage_after: number;
      next_review_at: string | null;
    }>('/me/reviews', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // Lessons
  completeLessons: (data: { item_ids: { item_type: string; item_id: number }[] }) =>
    request<unknown>('/me/lessons', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // Vocab
  getVocab: (params?: Record<string, string>) => {
    const qs = params ? '?' + new URLSearchParams(params).toString() : '';
    return request<VocabItem[]>(`/vocab${qs}`);
  },

  getVocabById: (id: number) => request<VocabItem>(`/vocab/${id}`),

  createVocab: (data: {
    word: string;
    readings: string[];
    meanings: string[];
    kanji_ids?: number[];
    tags?: string[];
    creator_comment?: string;
  }) =>
    request<VocabItem>('/vocab', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  searchVocab: (q: string, limit = 20) =>
    request<VocabSearchResult[]>(
      `/vocab/search?q=${encodeURIComponent(q)}&limit=${limit}`,
    ),

  updateVocab: (
    id: number,
    data: {
      word: string;
      readings: string[];
      meanings: string[];
      kanji_ids?: number[];
      tags?: string[];
      creator_comment?: string | null;
    },
  ) =>
    request<VocabItem>(`/vocab/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  deleteVocab: (id: number) =>
    requestNoBody(`/vocab/${id}`, { method: 'DELETE' }),

  updateSentence: (vocabId: number, sentenceId: number, ja: string, en: string) =>
    request<Sentence>(`/vocab/${vocabId}/sentences/${sentenceId}`, {
      method: 'PATCH',
      body: JSON.stringify({ ja, en }),
    }),

  createSentence: (vocabId: number, ja: string, en: string) =>
    request<Sentence>(`/vocab/${vocabId}/sentences`, {
      method: 'POST',
      body: JSON.stringify({ ja, en }),
    }),

  linkSentence: (vocabId: number, sentenceId: number) =>
    requestNoBody(`/vocab/${vocabId}/sentences/link`, {
      method: 'POST',
      body: JSON.stringify({ sentence_id: sentenceId }),
    }),

  unlinkSentence: (vocabId: number, sentenceId: number) =>
    requestNoBody(`/vocab/${vocabId}/sentences/${sentenceId}`, {
      method: 'DELETE',
    }),

  suggestSentences: (vocabId: number) =>
    request<Sentence[]>(`/vocab/${vocabId}/sentences/suggest`),

  searchSentences: (q: string) =>
    request<Sentence[]>(`/vocab/sentences/search?q=${encodeURIComponent(q)}`),

  // Kanji
  getKanji: (params?: Record<string, string>) => {
    const qs = params ? '?' + new URLSearchParams(params).toString() : '';
    return request<KanjiItem[]>(`/kanji${qs}`);
  },

  getKanjiDetail: (idOrChar: string) =>
    request<KanjiItem>(`/kanji/${encodeURIComponent(idOrChar)}`),

  // Progress
  getProgress: (params?: Record<string, string>) => {
    const qs = params ? '?' + new URLSearchParams(params).toString() : '';
    return request<ProgressItem[]>(`/me/progress${qs}`);
  },

  getProgressMap: async () => {
    const items = await request<ProgressItem[]>('/me/progress');
    const map: Record<string, number> = {};
    for (const item of items) {
      map[`${item.item_type}-${item.item_id}`] = item.srs_stage;
    }
    return map;
  },

  // Queue
  getQueue: async (): Promise<QueueItem[]> => {
    const res = await request<{ items: QueueItem[] }>('/me/queue');
    return res.items;
  },

  addToQueue: (item_type: string, item_id: number) =>
    request<QueueItem>('/me/queue', {
      method: 'POST',
      body: JSON.stringify({ item_type, item_id }),
    }),

  removeFromQueue: (item_type: string, item_id: number) =>
    requestNoBody(`/me/queue/${item_type}/${item_id}`, { method: 'DELETE' }),

  // Unlearn: delete progress (removes upcoming reviews); item is no longer learned or queued.
  unlearnItem: (item_type: string, item_id: number) =>
    requestNoBody(`/me/progress/${item_type}/${item_id}`, { method: 'DELETE' }),

  // Resurrect a burned item back to Apprentice 1.
  resurrectItem: (item_type: string, item_id: number) =>
    request<ProgressItem>(`/me/progress/${item_type}/${item_id}/resurrect`, { method: 'POST' }),
};

// Types

// A constituent kanji of a vocab word, for the Kanji Composition panel.
export interface KanjiComposition {
  character: string;
  meanings: string[];
}

export interface ReviewItem {
  item_type: string;
  item_id: number;
  srs_stage: number;
  next_review_at: string;
  item_details: {
    character?: string;
    word?: string;
    reading?: string;
    meanings: string[];
    readings_on?: string[];
    readings_kun?: string[];
    components?: string[];
    kanji?: KanjiComposition[];
  };
}

export interface Sentence {
  id: number;
  ja: string;
  en: string;
  added_by: number;
  created_at: string;
}

export interface DictionarySense {
  glosses: string[];
  pos: string[];
}

export interface VocabSearchResult {
  word: string;
  readings: string[];
  meanings: string[];
  pos: string[];
  senses: DictionarySense[];
  is_common: boolean;
  already_exists: boolean;
}

export interface VocabItem {
  id: number;
  word: string;
  readings: string[];
  meanings: string[];
  sentences: Sentence[];
  creator_username?: string;
  tags?: { id: number; name: string }[];
  // GET /vocab/{id} returns full kanji objects; the list endpoint may send a
  // lighter shape, so readings/meanings are optional.
  kanji?: { id: number; character: string; meanings?: string[]; readings_on?: string[]; readings_kun?: string[] }[];
  creator_comment?: string;
}

export interface KanjiItem {
  id: number;
  character: string;
  meanings: string[];
  readings_on: string[];
  readings_kun: string[];
  components: string[];
  grade?: number;
  jlpt_level?: number;
  stroke_count?: number;
  frequency?: number;
  active: boolean;
}

export interface ProgressItem {
  item_type: string;
  item_id: number;
  srs_stage: number;
  next_review_at: string | null;
  unlocked_at: string;
  burned_at: string | null;
  meaning_note: string | null;
  reading_mnemonic: string | null;
  source: string;
  item_details: {
    character?: string;
    word?: string;
    reading?: string;
    meanings: string[];
  };
}

export interface QueueItem {
  id: number;
  item_type: string;
  item_id: number;
  added_at: string;
  locked?: boolean;
  locked_by?: string[];
  item_details?: {
    character?: string;
    word?: string;
    reading?: string;
    meanings?: string[];
    readings?: string[];
    readings_on?: string[];
    readings_kun?: string[];
    components?: string[];
    kanji?: KanjiComposition[];
  };
}
