import { useState, useMemo, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Search, X } from 'lucide-react';
import {
  api,
  type KanjiItem,
  type VocabItem,
  type VocabSearchResult,
  type DictionarySense,
  type Sentence,
} from '../lib/api';
import { SRS_STAGE_COLORS, SRS_STAGE_NAMES } from '../lib/srs';
import { SubjectCard } from '../components/SubjectCard';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';

// Extract kanji characters from a string
function extractKanji(text: string): string[] {
  return [...text].filter((ch) => ch.charCodeAt(0) >= 0x4e00 && ch.charCodeAt(0) <= 0x9faf);
}

// Resolve the kanji items contained in a word, deduped, for auto-linking.
function useDetectedKanji(word: string): KanjiItem[] {
  const allKanji = useQuery({
    queryKey: ['kanji', 'all'],
    queryFn: () => api.getKanji({ include_inactive: 'true' }),
  });
  return useMemo(() => {
    if (!word || !allKanji.data) return [];
    const map = new Map(allKanji.data.map((k) => [k.character, k]));
    const found: KanjiItem[] = [];
    const seen = new Set<string>();
    for (const ch of extractKanji(word)) {
      if (!seen.has(ch)) {
        seen.add(ch);
        const k = map.get(ch);
        if (k) found.push(k);
      }
    }
    return found;
  }, [word, allKanji.data]);
}

// Add a vocab to the queue along with any constituent kanji the user isn't already
// learning (so the kanji get studied first — vocab stays locked until they're Guru).
// Returns how many kanji were newly queued. "Already queued" (409) is ignored.
export async function queueVocabAndKanji(
  vocabId: number,
  kanji: { id: number }[],
  progressMap: Record<string, number> | undefined,
): Promise<number> {
  const ignore409 = (e: unknown) => {
    if ((e as { status?: number })?.status !== 409) throw e;
  };
  await api.addToQueue('vocab', vocabId).catch(ignore409);
  let added = 0;
  for (const k of kanji) {
    if (progressMap?.[`kanji-${k.id}`] != null) continue; // already learning this kanji
    try {
      await api.addToQueue('kanji', k.id);
      added++;
    } catch (e) {
      ignore409(e);
    }
  }
  return added;
}

// Shows a word's auto-detected kanji with each one's SRS stage (or "New" if not yet
// started), plus any kanji that aren't in the pool at all.
function LinkedKanji({ word, kanji }: { word: string; kanji: KanjiItem[] }) {
  const progressMap = useQuery({ queryKey: ['progressMap'], queryFn: api.getProgressMap });
  const detectedChars = new Set(kanji.map((k) => k.character));
  const missing = [...new Set(extractKanji(word))].filter((ch) => !detectedChars.has(ch));

  if (kanji.length === 0 && missing.length === 0) return null;

  const hasNew = kanji.some((k) => progressMap.data?.[`kanji-${k.id}`] == null);

  return (
    <div>
      <Label className="mb-1 block text-xs text-muted-foreground">関連漢字（自動検出）</Label>
      <div className="flex gap-2 flex-wrap">
        {kanji.map((k) => {
          const stage = progressMap.data?.[`kanji-${k.id}`];
          return (
            <div key={k.id} className="flex flex-col items-center gap-1" title={k.meanings.join(', ')}>
              <div className="bg-wk-kanji w-9 h-9 rounded-lg flex items-center justify-center text-white font-bold">
                {k.character}
              </div>
              {stage != null ? (
                <span
                  className="text-[9px] font-bold px-1.5 py-0.5 rounded-full text-white whitespace-nowrap"
                  style={{ backgroundColor: SRS_STAGE_COLORS[stage] }}
                >
                  {SRS_STAGE_NAMES[stage]}
                </span>
              ) : (
                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-muted text-muted-foreground whitespace-nowrap">
                  新規
                </span>
              )}
            </div>
          );
        })}
        {missing.map((ch) => (
          <div key={ch} className="flex flex-col items-center gap-1" title="漢字プールに未登録">
            <div className="w-9 h-9 rounded-lg flex items-center justify-center font-bold border-2 border-dashed border-border text-muted-foreground">
              {ch}
            </div>
            <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-muted text-muted-foreground whitespace-nowrap">
              プール外
            </span>
          </div>
        ))}
      </div>
      {hasNew && (
        <p className="text-[11px] text-muted-foreground mt-1.5">
          学習キューに追加すると、上の「新規」漢字も一緒に追加され、先に学習できます。
        </p>
      )}
    </div>
  );
}

export function VocabPage() {
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [tagFilter, setTagFilter] = useState('');
  const [creatorFilter, setCreatorFilter] = useState('');
  const [hideKnown, setHideKnown] = useState(false);

  const params: Record<string, string> = {};
  if (tagFilter) params.tag = tagFilter;
  if (creatorFilter) params.creator = creatorFilter;

  const vocab = useQuery({
    queryKey: ['vocab', params],
    queryFn: () => api.getVocab(Object.keys(params).length ? params : undefined),
  });

  // Fetch all vocab (unfiltered) to extract tag/creator options
  const allVocab = useQuery({
    queryKey: ['vocab'],
    queryFn: () => api.getVocab(),
  });

  const allTags = useMemo(() => {
    const tags = new Set<string>();
    for (const v of allVocab.data || []) {
      for (const t of v.tags || []) tags.add(t.name);
    }
    return [...tags].sort();
  }, [allVocab.data]);

  const allCreators = useMemo(() => {
    const creators = new Set<string>();
    for (const v of allVocab.data || []) {
      if (v.creator_username) creators.add(v.creator_username);
    }
    return [...creators].sort();
  }, [allVocab.data]);

  const progressMap = useQuery({
    queryKey: ['progressMap'],
    queryFn: api.getProgressMap,
  });

  const items = useMemo(() => {
    let list = vocab.data || [];
    if (hideKnown && progressMap.data) {
      list = list.filter((v) => progressMap.data![`vocab-${v.id}`] == null);
    }
    return list;
  }, [vocab.data, hideKnown, progressMap.data]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">語彙</h1>
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground">
            {items.length}件
          </span>
          <Button
            variant={showCreate ? 'outline' : 'default'}
            onClick={() => setShowCreate(!showCreate)}
          >
            {showCreate ? 'キャンセル' : '＋新しい語彙'}
          </Button>
        </div>
      </div>

      {showCreate && (
        <CreateVocabForm
          onCreated={() => {
            setShowCreate(false);
            queryClient.invalidateQueries({ queryKey: ['vocab'] });
          }}
        />
      )}

      {/* Filters */}
      <div className="flex gap-3">
        <FilterDropdown
          placeholder="タグで絞り込み..."
          value={tagFilter}
          onChange={setTagFilter}
          options={allTags}
        />
        <FilterDropdown
          placeholder="作成者で絞り込み..."
          value={creatorFilter}
          onChange={setCreatorFilter}
          options={allCreators}
        />
        <Button
          variant={hideKnown ? 'secondary' : 'outline'}
          onClick={() => setHideKnown(!hideKnown)}
        >
          習得済みを隠す
        </Button>
      </div>

      {/* Vocab grid — compact blocks */}
      {vocab.isLoading ? (
        <div className="text-muted-foreground animate-pulse">読み込み中...</div>
      ) : items.length === 0 ? (
        <Card className="p-10 text-center text-muted-foreground">
          まだ語彙がありません。最初に追加してみましょう！
        </Card>
      ) : (
        <div className="flex flex-wrap gap-2">
          {items.map((item) => (
            <SubjectCard
              key={item.id}
              type="vocab"
              character={item.word}
              reading={item.readings[0]}
              meaning={item.meanings[0]}
              srsStage={progressMap.data?.[`vocab-${item.id}`]}
              to={`/vocab/${item.id}`}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function EditVocabForm({
  item,
  queryClient,
  onDone,
}: {
  item: VocabItem;
  queryClient: ReturnType<typeof useQueryClient>;
  onDone: () => void;
}) {
  const [word, setWord] = useState(item.word);
  const [readings, setReadings] = useState(item.readings.join(', '));
  const [meanings, setMeanings] = useState(item.meanings.join(', '));
  const [tags, setTags] = useState<string[]>((item.tags ?? []).map((t) => t.name));
  const [comment, setComment] = useState(item.creator_comment ?? '');
  const [error, setError] = useState('');

  const allTags = useAllTags();
  const detectedKanji = useDetectedKanji(word);

  const mutation = useMutation({
    mutationFn: () =>
      api.updateVocab(item.id, {
        word: word.trim(),
        readings: readings.split(',').map((r) => r.trim()).filter(Boolean),
        meanings: meanings.split(',').map((m) => m.trim()).filter(Boolean),
        kanji_ids: detectedKanji.map((k) => k.id),
        tags: tags,
        creator_comment: comment.trim() || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vocab'] });
      queryClient.invalidateQueries({ queryKey: ['progressMap'] });
      onDone();
    },
    onError: (err: Error) => setError(err.message),
  });

  const canSave = !!(word.trim() && readings.trim() && meanings.trim());

  return (
    <div className="px-5 py-4 space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label className="mb-1 block text-xs text-muted-foreground">単語</Label>
          <Input type="text" value={word} onChange={(e) => setWord(e.target.value)} className="h-auto py-2 text-lg" />
        </div>
        <div>
          <Label className="mb-1 block text-xs text-muted-foreground">読み（カンマ区切り）</Label>
          <Input type="text" value={readings} onChange={(e) => setReadings(e.target.value)} />
        </div>
      </div>

      <div>
        <Label className="mb-1 block text-xs text-muted-foreground">意味（カンマ区切り）</Label>
        <Input type="text" value={meanings} onChange={(e) => setMeanings(e.target.value)} />
      </div>

      <LinkedKanji word={word} kanji={detectedKanji} />

      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label className="mb-1 block text-xs text-muted-foreground">タグ</Label>
          <TagInput value={tags} onChange={setTags} options={allTags} />
        </div>
        <div>
          <Label className="mb-1 block text-xs text-muted-foreground">コメント</Label>
          <Input type="text" value={comment} onChange={(e) => setComment(e.target.value)} className="text-sm" />
        </div>
      </div>

      {error && <p className="text-destructive text-sm">{error}</p>}

      <div className="flex gap-2">
        <Button
          onClick={() => { if (canSave) { setError(''); mutation.mutate(); } }}
          disabled={!canSave || mutation.isPending}
        >
          {mutation.isPending ? '保存中...' : '変更を保存'}
        </Button>
        <Button variant="outline" onClick={onDone}>
          キャンセル
        </Button>
      </div>
    </div>
  );
}

function FilterDropdown({
  placeholder,
  value,
  onChange,
  options,
}: {
  placeholder: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
}) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState(value);

  const filtered = options.filter((o) =>
    o.toLowerCase().includes(input.toLowerCase()),
  );

  return (
    <div className="relative">
      <Input
        type="text"
        placeholder={placeholder}
        value={input}
        onChange={(e) => {
          setInput(e.target.value);
          setOpen(true);
          if (!e.target.value) onChange('');
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        className="w-48 pr-7 text-sm"
      />
      {value && (
        <button
          onClick={() => { setInput(''); onChange(''); }}
          className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
        >
          <X className="size-4" />
        </button>
      )}
      {open && filtered.length > 0 && (
        <div className="absolute top-full left-0 z-20 mt-1 max-h-48 w-full overflow-y-auto border border-border bg-popover p-1 shadow-md">
          {filtered.map((opt) => (
            <button
              key={opt}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => {
                setInput(opt);
                onChange(opt);
                setOpen(false);
              }}
              className="w-full px-2.5 py-1.5 text-left font-mono text-xs tracking-wider uppercase transition-colors hover:bg-accent hover:text-accent-foreground"
            >
              {opt}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// Existing tag names across the vocab pool, for tag suggestions. Reuses the
// cached ['vocab'] query so it's a cache hit on the Vocab page.
function useAllTags(): string[] {
  const allVocab = useQuery({
    queryKey: ['vocab'],
    queryFn: () => api.getVocab(),
  });
  return useMemo(() => {
    const tags = new Set<string>();
    for (const v of allVocab.data || []) {
      for (const t of v.tags || []) tags.add(t.name);
    }
    return [...tags].sort();
  }, [allVocab.data]);
}

// Multi-select tag editor: existing tags shown as a filtered dropdown, plus
// free entry of new tags (Enter / comma). Selected tags render as removable chips.
function TagInput({
  value,
  onChange,
  options,
}: {
  value: string[];
  onChange: (tags: string[]) => void;
  options: string[];
}) {
  const [input, setInput] = useState('');
  const [open, setOpen] = useState(false);

  const available = options.filter(
    (o) => !value.includes(o) && o.toLowerCase().includes(input.toLowerCase()),
  );

  const addTag = (tag: string) => {
    const t = tag.trim();
    if (t && !value.includes(t)) onChange([...value, t]);
    setInput('');
  };
  const removeTag = (tag: string) => onChange(value.filter((t) => t !== tag));

  return (
    <div className="relative">
      <div className="flex flex-wrap items-center gap-1.5 px-2 py-1.5 rounded-md border border-input bg-card focus-within:border-ring focus-within:ring-[3px] focus-within:ring-ring/40">
        {value.map((tag) => (
          <Badge key={tag} variant="secondary" className="gap-1">
            {tag}
            <button
              type="button"
              onClick={() => removeTag(tag)}
              className="leading-none hover:text-destructive"
            >
              <X className="size-3" />
            </button>
          </Badge>
        ))}
        <input
          type="text"
          value={input}
          placeholder={value.length ? '' : 'タグを追加...'}
          onChange={(e) => {
            const v = e.target.value;
            if (v.endsWith(',')) addTag(v.slice(0, -1));
            else setInput(v);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              if (input.trim()) addTag(input);
            } else if (e.key === 'Backspace' && !input && value.length) {
              removeTag(value[value.length - 1]);
            }
          }}
          className="flex-1 min-w-[80px] bg-transparent text-sm py-0.5 focus:outline-none"
        />
      </div>
      {open && available.length > 0 && (
        <div className="absolute top-full left-0 z-20 mt-1 max-h-48 w-full overflow-y-auto border border-border bg-popover p-1 shadow-md">
          {available.map((opt) => (
            <button
              key={opt}
              type="button"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => addTag(opt)}
              className="w-full px-2.5 py-1.5 text-left font-mono text-xs tracking-wider uppercase transition-colors hover:bg-accent hover:text-accent-foreground"
            >
              {opt}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function CreateVocabForm({ onCreated }: { onCreated: () => void }) {
  const queryClient = useQueryClient();
  const [word, setWord] = useState('');
  const [readings, setReadings] = useState('');
  const [meanings, setMeanings] = useState('');
  // Senses currently combined via shift-click, scoped to a single dictionary
  // entry (word). Switching entries starts fresh rather than stacking.
  const [selectedSenses, setSelectedSenses] = useState<{ word: string; indices: number[] }>({
    word: '',
    indices: [],
  });
  const [tags, setTags] = useState<string[]>([]);
  const [comment, setComment] = useState('');
  const allTags = useAllTags();
  const [sentences, setSentences] = useState<{ ja: string; en: string }[]>([]);
  const [showLinks, setShowLinks] = useState(false);
  const [linkIds, setLinkIds] = useState<Set<number>>(new Set());
  const [error, setError] = useState('');

  const toggleLink = (id: number) =>
    setLinkIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const addSentence = () => setSentences((prev) => [...prev, { ja: '', en: '' }]);
  const removeSentence = (i: number) =>
    setSentences((prev) => prev.filter((_, idx) => idx !== i));
  const updateSentence = (i: number, field: 'ja' | 'en', value: string) =>
    setSentences((prev) => prev.map((s, idx) => (idx === i ? { ...s, [field]: value } : s)));

  // Dictionary search (offline JMdict via backend) — prefills the fields below.
  const [dictQuery, setDictQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQuery(dictQuery.trim()), 300);
    return () => clearTimeout(t);
  }, [dictQuery]);

  const dictResults = useQuery({
    queryKey: ['vocabSearch', debouncedQuery],
    queryFn: () => api.searchVocab(debouncedQuery),
    enabled: debouncedQuery.length > 0,
  });

  // Picking a sense prefills the meanings with that sense's glosses (a JMdict
  // entry can have several distinct senses — e.g. 界隈 = "vicinity" vs.
  // "community/scene"). Plain click replaces the meanings and closes the list.
  // Shift-click builds up a combined selection scoped to a SINGLE entry: it
  // toggles the clicked sense and rebuilds the meanings from all selected senses
  // (deduped, in order). Shift-clicking a different entry starts fresh rather
  // than stacking across words. Editable afterwards.
  const applySense = (
    r: VocabSearchResult,
    senses: DictionarySense[],
    si: number,
    additive: boolean,
  ) => {
    setWord(r.word);
    setReadings(r.readings.join(', '));

    if (!additive) {
      setMeanings(senses[si].glosses.join(', '));
      setSelectedSenses({ word: r.word, indices: [si] });
      setDictQuery('');
      setDebouncedQuery('');
      return;
    }

    const sameWord = selectedSenses.word === r.word;
    let indices: number[];
    if (!sameWord) {
      indices = [si];
    } else if (selectedSenses.indices.includes(si)) {
      indices = selectedSenses.indices.filter((x) => x !== si); // toggle off
    } else {
      indices = [...selectedSenses.indices, si];
    }

    const glosses: string[] = [];
    for (const idx of indices) {
      for (const g of senses[idx].glosses) {
        if (!glosses.includes(g)) glosses.push(g);
      }
    }
    setMeanings(glosses.join(', '));
    setSelectedSenses({ word: r.word, indices });
  };

  // Auto-detect kanji from word
  const detectedKanji = useDetectedKanji(word);
  const progressMap = useQuery({ queryKey: ['progressMap'], queryFn: api.getProgressMap });

  // Existing pool sentences containing the word — for linking during creation.
  const linkSuggestions = useQuery({
    queryKey: ['sentenceSearch', word.trim()],
    queryFn: () => api.searchSentences(word.trim()),
    enabled: showLinks && word.trim().length > 0,
  });

  const mutation = useMutation({
    mutationFn: async ({ queue }: { queue: boolean }) => {
      const vocab = await api.createVocab({
        word: word.trim(),
        readings: readings.split(',').map((r) => r.trim()).filter(Boolean),
        meanings: meanings.split(',').map((m) => m.trim()).filter(Boolean),
        kanji_ids: detectedKanji.map((k) => k.id),
        tags: tags.length ? tags : undefined,
        creator_comment: comment.trim() || undefined,
      });
      for (const s of sentences) {
        if (s.ja.trim() && s.en.trim()) {
          await api.createSentence(vocab.id, s.ja.trim(), s.en.trim());
        }
      }
      for (const id of linkIds) {
        await api.linkSentence(vocab.id, id);
      }
      if (queue) await queueVocabAndKanji(vocab.id, detectedKanji, progressMap.data);
      return vocab;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['queue'] });
      onCreated();
    },
    onError: (err: Error) => setError(err.message),
  });

  const submit = (queue: boolean) => {
    if (!word.trim() || !readings.trim() || !meanings.trim()) return;
    setError('');
    mutation.mutate({ queue });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    submit(true);
  };

  return (
    <form onSubmit={handleSubmit} className="bg-card text-card-foreground flex flex-col gap-3 rounded-xl border p-5 shadow-sm">
      <h2 className="font-bold text-lg">語彙を追加</h2>

        {/* Dictionary search — pick a result to prefill the fields below */}
        <div>
          <Label className="mb-1 block text-xs text-muted-foreground">辞書を検索（日本語）</Label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="例：食べ、たべる など"
              value={dictQuery}
              onChange={(e) => setDictQuery(e.target.value)}
              className="pl-9"
            />
          </div>

          {debouncedQuery.length > 0 && (
            <div className="mt-1 border border-border rounded-md bg-popover max-h-64 overflow-y-auto divide-y divide-border">
              {dictResults.isLoading && (
                <p className="px-3 py-2 text-sm text-muted-foreground animate-pulse">検索中...</p>
              )}
              {dictResults.data?.length === 0 && (
                <p className="px-3 py-2 text-sm text-muted-foreground">辞書に一致する項目がありません。</p>
              )}
              {dictResults.data?.map((r, i) => {
                // Fall back to a single synthetic sense for entries without a
                // per-sense breakdown (back-compat).
                const senses: DictionarySense[] = r.senses?.length
                  ? r.senses
                  : [{ glosses: r.meanings, pos: r.pos }];
                return (
                  <div key={`${r.word}-${i}`} className="px-3 py-2">
                    <div className="flex items-center gap-3 mb-1">
                      <span className="text-lg font-bold shrink-0" lang="ja">{r.word}</span>
                      <span className="text-sm text-muted-foreground shrink-0" lang="ja">{r.readings.slice(0, 2).join('、')}</span>
                      {r.is_common && !r.already_exists && (
                        <span className="text-[10px] font-bold text-success shrink-0">● 常用</span>
                      )}
                      {r.already_exists && (
                        <span className="text-[10px] font-bold text-muted-foreground shrink-0">✓ 登録済み</span>
                      )}
                    </div>
                    <div className="space-y-0.5">
                      {senses.map((s, si) => {
                        const selected =
                          selectedSenses.word === r.word && selectedSenses.indices.includes(si);
                        return (
                          <button
                            key={si}
                            type="button"
                            disabled={r.already_exists}
                            onClick={(e) => applySense(r, senses, si, e.shiftKey)}
                            title="クリックでこの意味を使用 · Shift＋クリックで意味を組み合わせ"
                            className={cn(
                              'w-full text-left text-sm rounded px-2 py-1 flex gap-2 transition-colors',
                              r.already_exists
                                ? 'opacity-50 cursor-not-allowed'
                                : selected
                                  ? 'bg-accent text-accent-foreground font-medium cursor-pointer'
                                  : 'hover:bg-accent cursor-pointer',
                            )}
                          >
                            {senses.length > 1 && (
                              <span className="shrink-0 tabular-nums text-muted-foreground">
                                {selected ? '✓' : `${si + 1}.`}
                              </span>
                            )}
                            <span className="flex-1 min-w-0">{s.glosses.join('; ')}</span>
                          </button>
                        );
                      })}
                    </div>
                    {senses.length > 1 && !r.already_exists && (
                      <p className="text-[10px] text-muted-foreground mt-1">
                        Shift＋クリックで意味を組み合わせ · もう一度クリックで解除。
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label className="mb-1 block text-xs text-muted-foreground">単語</Label>
            <Input
              type="text"
              placeholder="例：食べ物"
              value={word}
              onChange={(e) => setWord(e.target.value)}
              className="h-auto py-2 text-lg"
              required
            />
          </div>
          <div>
            <Label className="mb-1 block text-xs text-muted-foreground">読み（カンマ区切り）</Label>
            <Input
              type="text"
              placeholder="例：たべもの"
              value={readings}
              onChange={(e) => setReadings(e.target.value)}
              required
            />
          </div>
        </div>

        <div>
          <Label className="mb-1 block text-xs text-muted-foreground">意味（カンマ区切り）</Label>
          <Input
            type="text"
            placeholder="例：food, provisions"
            value={meanings}
            onChange={(e) => setMeanings(e.target.value)}
            required
          />
        </div>

        {/* Auto-detected kanji */}
        <LinkedKanji word={word} kanji={detectedKanji} />

        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label className="mb-1 block text-xs text-muted-foreground">タグ（任意）</Label>
            <TagInput value={tags} onChange={setTags} options={allTags} />
          </div>
          <div>
            <Label className="mb-1 block text-xs text-muted-foreground">コメント（任意）</Label>
            <Input
              type="text"
              placeholder="この単語をどこで見つけましたか？"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              className="text-sm"
            />
          </div>
        </div>

        {/* Example sentences (optional) */}
        <div>
          <Label className="mb-1 block text-xs text-muted-foreground">例文（任意）</Label>
          <div className="space-y-2">
            {sentences.map((s, i) => (
              <div key={i} className="flex gap-2">
                <div className="flex-1 space-y-1">
                  <Input
                    type="text"
                    value={s.ja}
                    onChange={(e) => updateSentence(i, 'ja', e.target.value)}
                    placeholder="日本語..."
                    lang="ja"
                    className="h-auto py-1.5 text-sm"
                  />
                  <Input
                    type="text"
                    value={s.en}
                    onChange={(e) => updateSentence(i, 'en', e.target.value)}
                    placeholder="英語..."
                    className="h-auto py-1.5 text-sm"
                  />
                </div>
                <button
                  type="button"
                  onClick={() => removeSentence(i)}
                  className="self-start text-muted-foreground hover:text-destructive text-lg leading-none px-1"
                  title="例文を削除"
                >
                  &times;
                </button>
              </div>
            ))}
            <Button
              type="button"
              variant="link"
              size="sm"
              onClick={addSentence}
              className="h-auto p-0 text-wk-vocab font-bold"
            >
              ＋例文を追加
            </Button>
          </div>
        </div>

        {/* Find & link existing pool sentences containing this word */}
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Label className="text-xs text-muted-foreground">既存の例文をリンク（任意）</Label>
            <Button
              type="button"
              variant="link"
              size="sm"
              onClick={() => setShowLinks((v) => !v)}
              disabled={!word.trim()}
              className="h-auto p-0 text-wk-vocab font-bold"
            >
              {showLinks ? '隠す' : '例文を探す'}
            </Button>
            {linkIds.size > 0 && (
              <span className="text-xs text-muted-foreground">{linkIds.size}件選択中</span>
            )}
          </div>

          {showLinks && word.trim() && (
            <div className="space-y-1">
              {linkSuggestions.isLoading && (
                <p className="text-xs text-muted-foreground animate-pulse">検索中…</p>
              )}
              {linkSuggestions.data?.length === 0 && (
                <p className="text-xs text-muted-foreground">「{word.trim()}」を含む既存の例文はありません。</p>
              )}
              {linkSuggestions.data?.map((s: Sentence) => {
                const selected = linkIds.has(s.id);
                return (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => toggleLink(s.id)}
                    className={cn(
                      'w-full text-left rounded-md px-3 py-1.5 text-sm flex items-center gap-2 transition-colors',
                      selected ? 'bg-accent text-accent-foreground ring-1 ring-primary' : 'bg-muted hover:bg-accent',
                    )}
                  >
                    <span className={cn('shrink-0', selected ? 'text-primary' : 'text-muted-foreground')}>
                      {selected ? '☑' : '☐'}
                    </span>
                    <span className="flex-1 min-w-0">
                      <span lang="ja">{s.ja}</span>
                      <span className="text-muted-foreground text-xs ml-2">{s.en}</span>
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {error && <p className="text-destructive text-sm">{error}</p>}

        <div className="flex gap-2">
          <Button
            type="submit"
            disabled={mutation.isPending || !word.trim() || !readings.trim() || !meanings.trim()}
          >
            {mutation.isPending ? '保存中...' : '作成して学習キューに追加'}
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => submit(false)}
            disabled={mutation.isPending || !word.trim() || !readings.trim() || !meanings.trim()}
          >
            作成のみ
          </Button>
        </div>
    </form>
  );
}
