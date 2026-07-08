import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, type Politeness } from '../lib/api';
import { SRS_STAGE_COLORS, SRS_STAGE_NAMES } from '../lib/srs';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card } from '@/components/ui/card';

// Politeness → short JP label + tint. mixed = "anything goes" per design.
const POLITENESS: Record<Politeness, { label: string; className: string }> = {
  polite: { label: '丁寧', className: 'bg-wk-sentence/15 text-wk-sentence' },
  casual: { label: '普通体', className: 'bg-muted text-muted-foreground' },
  mixed: { label: '混在', className: 'bg-muted text-muted-foreground' },
};

export function PolitenessBadge({ value }: { value: Politeness }) {
  const p = POLITENESS[value];
  return (
    <span className={cn('shrink-0 px-1.5 py-0.5 font-mono text-[10px] tracking-wider uppercase', p.className)}>
      {p.label}
    </span>
  );
}

export function StageBadge({ stage }: { stage: number }) {
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
