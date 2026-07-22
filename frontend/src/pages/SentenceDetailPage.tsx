import { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, X } from 'lucide-react';
import { api } from '../lib/api';
import { romajiToHiraganaLive } from '../lib/romaji';
import { cn } from '@/lib/utils';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { PolitenessBadge, StageBadge } from './SentencesPage';

// Linked grammar points + post-add corrections (unlink / hand-attach from the bank).
function GrammarSection({ sentenceId }: { sentenceId: number }) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ['sentence', sentenceId],
    queryFn: () => api.getSentence(sentenceId),
  });
  const bank = useQuery({ queryKey: ['grammarPoints'], queryFn: api.getGrammarPoints });
  const grammar = query.data?.grammar ?? [];

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['sentence', sentenceId] });
    queryClient.invalidateQueries({ queryKey: ['grammarPoints'] });
  };
  const detachMut = useMutation({
    mutationFn: (pointId: number) => api.detachSentenceGrammar(sentenceId, pointId),
    onSuccess: invalidate,
  });
  const [filter, setFilter] = useState('');
  const attachMut = useMutation({
    mutationFn: (pointId: number) => api.attachSentenceGrammar(sentenceId, pointId),
    onSuccess: () => {
      setFilter('');
      invalidate();
    },
  });

  const linkedIds = new Set(grammar.map((g) => g.grammar_point_id));
  const attachable = (bank.data ?? []).filter((p) => !linkedIds.has(p.grammar_point_id));

  // Type-to-filter: raw text matches key/gloss; romaji is also converted live to hiragana so
  // "niyoru" finds 〜による without an IME.
  const q = filter.trim().toLowerCase();
  const kanaQ = romajiToHiraganaLive(q);
  const matches = q
    ? attachable
        .filter(
          (p) =>
            p.key.toLowerCase().includes(q) ||
            p.meaning_en.toLowerCase().includes(q) ||
            (kanaQ && p.key.includes(kanaQ)),
        )
        .slice(0, 8)
    : [];

  return (
    <div>
      <h2 className="mb-2 font-mono text-xs uppercase tracking-wider text-muted-foreground">
        文法（{grammar.length}）
      </h2>
      {grammar.length === 0 ? (
        <p className="text-sm text-muted-foreground">文法ポイントはまだ抽出されていません。</p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {grammar.map((g) => (
            <span
              key={g.grammar_point_id}
              className="inline-flex items-center gap-2 border border-wk-sentence/40 bg-wk-sentence/10 py-1 pl-2.5 pr-1"
            >
              <Link
                to={`/grammar/${g.grammar_point_id}`}
                className="flex items-baseline gap-2 hover:underline"
                title={g.evidence ? `「${g.evidence}」` : undefined}
              >
                <span lang="ja" className="font-[family-name:var(--font-mincho)]">
                  {g.key}
                </span>
                <span className="text-xs text-muted-foreground">{g.meaning_en}</span>
              </Link>
              <button
                onClick={() => detachMut.mutate(g.grammar_point_id)}
                disabled={detachMut.isPending}
                className="text-muted-foreground transition-colors hover:text-destructive"
                title="この文から外す"
              >
                <X className="size-3.5" />
              </button>
            </span>
          ))}
        </div>
      )}
      {attachable.length > 0 && (
        <div className="relative mt-3 max-w-sm">
          <input
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="文法ポイントを追加… (かな/romaji/english)"
            lang="ja"
            className="w-full border border-input bg-card px-3 py-1.5 text-sm focus:border-ring focus:ring-[3px] focus:ring-ring/40 focus:outline-none"
          />
          {matches.length > 0 && (
            <div className="absolute z-10 mt-1 w-full divide-y divide-border border border-border bg-card shadow-sm">
              {matches.map((p) => (
                <button
                  key={p.grammar_point_id}
                  onClick={() => attachMut.mutate(p.grammar_point_id)}
                  disabled={attachMut.isPending}
                  className="flex w-full items-baseline gap-2 px-3 py-1.5 text-left transition-colors hover:bg-accent/50"
                >
                  <span lang="ja" className="font-[family-name:var(--font-mincho)]">
                    {p.key}
                  </span>
                  <span className="min-w-0 truncate text-xs text-muted-foreground">
                    {p.meaning_en}
                  </span>
                </button>
              ))}
            </div>
          )}
          {q && matches.length === 0 && (
            <p className="mt-1 text-xs text-muted-foreground">一致する文法ポイントがありません。</p>
          )}
        </div>
      )}
      {(detachMut.isError || attachMut.isError) && (
        <p className="mt-2 text-sm text-destructive">
          {((detachMut.error || attachMut.error) as Error).message}
        </p>
      )}
    </div>
  );
}

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

          <GrammarSection sentenceId={sentenceId} />

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
