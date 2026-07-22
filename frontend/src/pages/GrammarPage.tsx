import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import { Card } from '@/components/ui/card';

// The personal grammar bank: minted automatically from production sentences (no direct add).
// Sorted most-used first by the API; noise sinks to the bottom naturally.
export function GrammarPage() {
  const query = useQuery({ queryKey: ['grammarPoints'], queryFn: api.getGrammarPoints });
  const points = query.data ?? [];

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="flex items-baseline justify-between">
        <h1 className="text-2xl font-bold">文法</h1>
        <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
          {points.length}件
        </span>
      </div>
      <p className="text-sm text-muted-foreground">
        作文から自動抽出された文法ポイント。文を追加すると増えていきます。
      </p>

      {query.isLoading ? (
        <div className="animate-pulse text-muted-foreground">読み込み中...</div>
      ) : points.length === 0 ? (
        <Card className="p-10 text-center text-muted-foreground">
          まだ文法ポイントがありません。作文を追加すると自動で抽出されます。
        </Card>
      ) : (
        <div className="divide-y divide-border border border-border">
          {points.map((p) => (
            <Link
              key={p.grammar_point_id}
              to={`/grammar/${p.grammar_point_id}`}
              className="flex items-center gap-3 px-4 py-3 transition-colors hover:bg-accent/50"
            >
              <span lang="ja" className="text-lg font-[family-name:var(--font-mincho)]">
                {p.key}
              </span>
              <span className="min-w-0 truncate text-sm text-muted-foreground">
                {p.meaning_en}
              </span>
              <span className="ml-auto shrink-0 bg-wk-sentence/15 px-1.5 py-0.5 font-mono text-[10px] font-bold text-wk-sentence">
                {p.sentence_count}文
              </span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
