import { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft } from 'lucide-react';
import { api } from '../lib/api';
import { cn } from '@/lib/utils';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { PolitenessBadge, StageBadge } from './SentencesPage';

export function SentenceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const sentenceId = Number(id);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ['sentence', sentenceId],
    queryFn: () => api.getSentence(sentenceId),
    enabled: Number.isFinite(sentenceId),
  });
  const s = query.data;

  const deleteMut = useMutation({
    mutationFn: () => api.deleteSentence(sentenceId),
    onSuccess: () => {
      // Drop it from the list, review/lesson queues, and the dashboard counts.
      for (const key of ['sentences', 'sentenceReviews', 'sentenceLessons', 'progressMap']) {
        queryClient.invalidateQueries({ queryKey: [key] });
      }
      navigate('/sentences');
    },
  });

  const handleDelete = () => {
    if (!s) return;
    if (
      window.confirm(
        `この作文を削除しますか？\n\n「${s.english}」\n\n` +
          `復習履歴とSRS進捗も削除されます。この操作は取り消せません。`,
      )
    ) {
      deleteMut.mutate();
    }
  };

  const [editing, setEditing] = useState(false);
  const [editEn, setEditEn] = useState('');
  const [editJa, setEditJa] = useState('');

  // Edit re-validates the pair (LLM) and re-derives politeness, like create. SRS/history kept.
  const editMut = useMutation({
    mutationFn: () => api.editSentence(sentenceId, editEn.trim(), editJa.trim()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sentence', sentenceId] });
      queryClient.invalidateQueries({ queryKey: ['sentences'] });
      setEditing(false);
    },
  });

  const startEdit = () => {
    if (!s) return;
    setEditEn(s.english);
    setEditJa(s.japanese);
    editMut.reset();
    setEditing(true);
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="flex items-center justify-between">
        <Link
          to="/sentences"
          className="inline-flex items-center gap-1.5 font-mono text-xs font-semibold uppercase tracking-wider text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="size-3.5" />
          作文
        </Link>
        {s && !editing && (
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={startEdit}>
              編集
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleDelete}
              disabled={deleteMut.isPending}
              className="border-destructive/40 text-destructive hover:bg-destructive/10 hover:text-destructive"
            >
              {deleteMut.isPending ? '削除中…' : '削除'}
            </Button>
          </div>
        )}
      </div>
      {deleteMut.isError && (
        <p className="text-sm text-destructive">{(deleteMut.error as Error).message}</p>
      )}

      {query.isLoading ? (
        <div className="text-muted-foreground animate-pulse">読み込み中...</div>
      ) : query.isError || !s ? (
        <Card className="p-10 text-center text-muted-foreground">文が見つかりません。</Card>
      ) : (
        <>
          {editing ? (
            <div className="space-y-4 border-l-4 border-wk-sentence bg-card p-6">
              <div>
                <label className="mb-1 block font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                  英語
                </label>
                <textarea
                  value={editEn}
                  onChange={(e) => setEditEn(e.target.value)}
                  rows={2}
                  className="w-full resize-y border border-input bg-card px-3 py-2 text-sm focus:border-ring focus:ring-[3px] focus:ring-ring/40 focus:outline-none"
                />
              </div>
              <div>
                <label className="mb-1 block font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                  日本語
                </label>
                <textarea
                  value={editJa}
                  onChange={(e) => setEditJa(e.target.value)}
                  rows={2}
                  lang="ja"
                  className="w-full resize-y border border-input bg-card px-3 py-2 font-[family-name:var(--font-mincho)] focus:border-ring focus:ring-[3px] focus:ring-ring/40 focus:outline-none"
                />
              </div>
              <p className="font-mono text-[10px] text-muted-foreground">
                保存時にペアを再検証し、丁寧さを自動判定します。SRSの進捗と履歴は保持されます。
              </p>
              {editMut.isError && (
                <p className="text-sm text-destructive">{(editMut.error as Error).message}</p>
              )}
              <div className="flex gap-2">
                <Button
                  size="sm"
                  onClick={() => editMut.mutate()}
                  disabled={editMut.isPending || !editEn.trim() || !editJa.trim()}
                >
                  {editMut.isPending ? '検証中…' : '保存'}
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setEditing(false)}
                  disabled={editMut.isPending}
                >
                  取消
                </Button>
              </div>
            </div>
          ) : (
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
          )}

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
