import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, type Politeness } from '../lib/api';
import { SRS_STAGE_COLORS, SRS_STAGE_NAMES } from '../lib/srs';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card } from '@/components/ui/card';

// Politeness = a formality dial, color-coded so it reads at a glance:
// 丁寧 blue (formal) · 普通体 amber (relaxed) · 混在 slate (no constraint).
// A colored square dot + tinted chip (mid-tone hues read on both light & dark).
const POLITENESS: Record<Politeness, { label: string; color: string }> = {
  polite: { label: '丁寧', color: '#5b8def' },
  casual: { label: '普通体', color: '#d99a2b' },
  mixed: { label: '混在', color: '#8a93a3' },
};

export function PolitenessBadge({ value }: { value: Politeness }) {
  const p = POLITENESS[value];
  return (
    <span
      className="inline-flex shrink-0 items-center gap-1.5 border px-2 py-0.5 font-mono text-[10px] font-semibold tracking-wider uppercase"
      style={{
        color: p.color,
        backgroundColor: `color-mix(in srgb, ${p.color} 14%, transparent)`,
        borderColor: `color-mix(in srgb, ${p.color} 40%, transparent)`,
      }}
    >
      <span className="size-1.5" style={{ backgroundColor: p.color }} />
      {p.label}
    </span>
  );
}

export function StageBadge({ stage }: { stage: number | null }) {
  // null = pending lesson (created, not yet learned).
  if (stage == null) {
    return (
      <span className="shrink-0 whitespace-nowrap bg-wk-sentence/15 px-1.5 py-0.5 text-[10px] font-bold text-wk-sentence">
        レッスン待ち
      </span>
    );
  }
  return (
    <span
      className="shrink-0 px-1.5 py-0.5 text-[10px] font-bold whitespace-nowrap text-white"
      style={{ backgroundColor: SRS_STAGE_COLORS[stage] }}
    >
      {SRS_STAGE_NAMES[stage]}
    </span>
  );
}

export function SentencesPage() {
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);

  const sentences = useQuery({ queryKey: ['sentences'], queryFn: api.getSentences });
  const items = sentences.data ?? [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">作文</h1>
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground">{items.length}件</span>
          <Button
            variant={showCreate ? 'outline' : 'default'}
            onClick={() => setShowCreate((v) => !v)}
          >
            {showCreate ? 'キャンセル' : '＋新しい文'}
          </Button>
        </div>
      </div>

      {showCreate && (
        <CreateSentenceForm
          onCreated={() => {
            setShowCreate(false);
            queryClient.invalidateQueries({ queryKey: ['sentences'] });
          }}
        />
      )}

      {sentences.isLoading ? (
        <div className="text-muted-foreground animate-pulse">読み込み中...</div>
      ) : items.length === 0 ? (
        <Card className="p-10 text-center text-muted-foreground">
          まだ文がありません。英語と日本語の文を追加してみましょう！
        </Card>
      ) : (
        <div className="divide-y divide-border border border-border">
          {items.map((s) => (
            <Link
              key={s.sentence_id}
              to={`/sentences/${s.sentence_id}`}
              className="flex items-center gap-3 px-4 py-3 transition-colors hover:bg-accent"
            >
              <span className="w-1 shrink-0 self-stretch bg-wk-sentence" />
              <div className="min-w-0 flex-1">
                <div lang="ja" className="truncate font-[family-name:var(--font-mincho)]">
                  {s.japanese}
                </div>
                <div className="truncate text-sm text-muted-foreground">{s.english}</div>
              </div>
              <PolitenessBadge value={s.politeness} />
              <StageBadge stage={s.srs_stage} />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function CreateSentenceForm({ onCreated }: { onCreated: () => void }) {
  const [english, setEnglish] = useState('');
  const [japanese, setJapanese] = useState('');
  const [error, setError] = useState('');

  const mutation = useMutation({
    mutationFn: () => api.createProductionSentence(english.trim(), japanese.trim()),
    onSuccess: onCreated,
    // 422 = pair rejected by the LLM validator; detail explains why (actionable).
    onError: (err: Error) => setError(err.message),
  });

  const canSubmit = !!(english.trim() && japanese.trim()) && !mutation.isPending;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setError('');
    mutation.mutate();
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-3 border border-border bg-card p-5 text-card-foreground"
    >
      <h2 className="text-lg font-bold">文を追加</h2>
      <p className="text-xs text-muted-foreground">
        英語と日本語のペアを追加。AIがペアを検証してから保存します（不自然・不一致は却下）。
      </p>

      <div>
        <Label className="mb-1 block text-xs text-muted-foreground">英語（プロンプト）</Label>
        <Input
          type="text"
          placeholder="例：5 more days."
          value={english}
          onChange={(e) => setEnglish(e.target.value)}
          required
        />
      </div>

      <div>
        <Label className="mb-1 block text-xs text-muted-foreground">日本語（解答）</Label>
        <textarea
          lang="ja"
          placeholder="例：あと5日。"
          value={japanese}
          onChange={(e) => setJapanese(e.target.value)}
          rows={2}
          className="w-full resize-y border border-input bg-card px-3 py-2 font-[family-name:var(--font-mincho)] focus:border-ring focus:ring-[3px] focus:ring-ring/40 focus:outline-none"
          required
        />
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <div className="flex gap-2">
        <Button type="submit" disabled={!canSubmit}>
          {mutation.isPending ? '検証中...' : '検証して追加'}
        </Button>
      </div>
    </form>
  );
}
