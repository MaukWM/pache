import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft } from 'lucide-react';
import { api } from '../lib/api';
import { cn } from '@/lib/utils';
import { Card } from '@/components/ui/card';
import { PolitenessBadge, StageBadge } from './SentencesPage';

export function SentenceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const sentenceId = Number(id);

  const query = useQuery({
    queryKey: ['sentence', sentenceId],
    queryFn: () => api.getSentence(sentenceId),
    enabled: Number.isFinite(sentenceId),
  });
  const s = query.data;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Link
        to="/sentences"
        className="inline-flex items-center gap-1.5 font-mono text-xs font-semibold uppercase tracking-wider text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="size-3.5" />
        作文
      </Link>

      {query.isLoading ? (
        <div className="text-muted-foreground animate-pulse">読み込み中...</div>
      ) : query.isError || !s ? (
        <Card className="p-10 text-center text-muted-foreground">文が見つかりません。</Card>
      ) : (
        <>
          <div className="space-y-4 border-l-4 border-wk-sentence bg-card p-6">
            <div>
              <div className="mb-1 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                日本語
              </div>
              <div lang="ja" className="text-2xl font-[family-name:var(--font-mincho)]">
                {s.japanese}
              </div>
            </div>
            <div>
              <div className="mb-1 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                英語
              </div>
              <div className="text-lg text-muted-foreground">{s.english}</div>
            </div>
            <div className="flex items-center gap-2 pt-1">
              <PolitenessBadge value={s.politeness} />
              <StageBadge stage={s.srs_stage} />
              <span className="ml-auto font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                {new Date(s.created_at).toLocaleDateString()}
              </span>
            </div>
          </div>

          <div>
            <h2 className="mb-2 font-mono text-xs uppercase tracking-wider text-muted-foreground">
              復習履歴（{s.reviews.length}）
            </h2>
            {s.reviews.length === 0 ? (
              <p className="text-sm text-muted-foreground">まだ復習していません。</p>
            ) : (
              <div className="divide-y divide-border border border-border">
                {s.reviews.map((r, i) => (
                  <div key={i} className="space-y-1 px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span
                        className={cn(
                          'shrink-0 px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wider',
                          r.correct
                            ? 'bg-success/15 text-success'
                            : 'bg-destructive/15 text-destructive',
                        )}
                      >
                        {r.correct ? '正解' : '不正解'}
                      </span>
                      {r.exact_match && (
                        <span className="shrink-0 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                          完全一致
                        </span>
                      )}
                      {r.overridden && (
                        <span className="shrink-0 bg-wk-sentence/15 px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wider text-wk-sentence">
                          上書き
                        </span>
                      )}
                      <span className="ml-auto font-mono text-[10px] text-muted-foreground">
                        {r.srs_stage_before} → {r.srs_stage_after}
                      </span>
                    </div>
                    <div lang="ja" className="font-[family-name:var(--font-mincho)]">
                      {r.submitted}
                    </div>
                    {r.feedback && <p className="text-sm text-muted-foreground">{r.feedback}</p>}
                    {r.override_reason && (
                      <p className="text-xs text-muted-foreground">
                        上書き理由: {r.override_reason}
                      </p>
                    )}
                    <div className="font-mono text-[10px] text-muted-foreground">
                      {new Date(r.reviewed_at).toLocaleString()}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
