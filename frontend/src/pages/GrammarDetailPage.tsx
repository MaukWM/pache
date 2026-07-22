import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft } from 'lucide-react';
import { api } from '../lib/api';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { StageBadge } from './SentencesPage';
import { AccuracyBadge } from './GrammarPage';

// One grammar point + every sentence that exercises it (evidence = the substring that
// instantiates the point — matters for abstract keys like 受身形 that never appear literally).
export function GrammarDetailPage() {
  const { id } = useParams<{ id: string }>();
  const pointId = Number(id);
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ['grammarPoint', pointId],
    queryFn: () => api.getGrammarPoint(pointId),
    enabled: Number.isFinite(pointId),
  });
  const p = query.data;

  const [editing, setEditing] = useState(false);
  const [editKey, setEditKey] = useState('');
  const [editMeaning, setEditMeaning] = useState('');

  // Rename fixes a mis-minted key/gloss (e.g. homograph collision). Links stay.
  const renameMut = useMutation({
    mutationFn: () => api.updateGrammarPoint(pointId, { key: editKey.trim(), meaning_en: editMeaning.trim() }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['grammarPoint', pointId] });
      queryClient.invalidateQueries({ queryKey: ['grammarPoints'] });
      setEditing(false);
    },
  });

  const startEdit = () => {
    if (!p) return;
    setEditKey(p.key);
    setEditMeaning(p.meaning_en);
    renameMut.reset();
    setEditing(true);
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="flex items-center justify-between">
        <Link
          to="/grammar"
          className="inline-flex items-center gap-1.5 font-mono text-xs font-semibold uppercase tracking-wider text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="size-3.5" />
          文法
        </Link>
        {p && !editing && (
          <Button variant="outline" size="sm" onClick={startEdit}>
            編集
          </Button>
        )}
      </div>

      {query.isLoading ? (
        <div className="animate-pulse text-muted-foreground">読み込み中...</div>
      ) : query.isError || !p ? (
        <Card className="p-10 text-center text-muted-foreground">
          文法ポイントが見つかりません。
        </Card>
      ) : (
        <>
          {editing ? (
            <div className="space-y-4 border-l-4 border-wk-sentence bg-card p-6">
              <div>
                <label className="mb-1 block font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                  キー
                </label>
                <input
                  value={editKey}
                  onChange={(e) => setEditKey(e.target.value)}
                  lang="ja"
                  className="w-full border border-input bg-card px-3 py-2 font-[family-name:var(--font-mincho)] focus:border-ring focus:ring-[3px] focus:ring-ring/40 focus:outline-none"
                />
              </div>
              <div>
                <label className="mb-1 block font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                  意味
                </label>
                <input
                  value={editMeaning}
                  onChange={(e) => setEditMeaning(e.target.value)}
                  className="w-full border border-input bg-card px-3 py-2 text-sm focus:border-ring focus:ring-[3px] focus:ring-ring/40 focus:outline-none"
                />
              </div>
              {renameMut.isError && (
                <p className="text-sm text-destructive">{(renameMut.error as Error).message}</p>
              )}
              <div className="flex gap-2">
                <Button
                  size="sm"
                  onClick={() => renameMut.mutate()}
                  disabled={renameMut.isPending || !editKey.trim() || !editMeaning.trim()}
                >
                  保存
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setEditing(false)}
                  disabled={renameMut.isPending}
                >
                  取消
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-2 border-l-4 border-wk-sentence bg-card p-6">
              <div lang="ja" className="text-3xl font-[family-name:var(--font-mincho)]">
                {p.key}
              </div>
              <div className="text-lg text-muted-foreground">{p.meaning_en}</div>
              <div className="flex items-center gap-3 pt-1">
                <AccuracyBadge correct={p.correct_count} total={p.review_count} />
                <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                  {new Date(p.created_at).toLocaleDateString()} に追加
                </span>
              </div>
            </div>
          )}

          <div>
            <h2 className="mb-2 font-mono text-xs uppercase tracking-wider text-muted-foreground">
              使われている文（{p.sentences.length}）
            </h2>
            {p.sentences.length === 0 ? (
              <p className="text-sm text-muted-foreground">この文法を使う文はありません。</p>
            ) : (
              <div className="divide-y divide-border border border-border">
                {p.sentences.map((s) => (
                  <Link
                    key={s.sentence_id}
                    to={`/sentences/${s.sentence_id}`}
                    className="block space-y-1 px-4 py-3 transition-colors hover:bg-accent/50"
                  >
                    <div className="flex items-start gap-2">
                      <span lang="ja" className="min-w-0 font-[family-name:var(--font-mincho)]">
                        {s.japanese}
                      </span>
                      <span className="ml-auto shrink-0">
                        <StageBadge stage={s.srs_stage} />
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground">{s.english}</p>
                    {s.evidence && (
                      <p className="font-mono text-[10px] text-wk-sentence">「{s.evidence}」</p>
                    )}
                  </Link>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
