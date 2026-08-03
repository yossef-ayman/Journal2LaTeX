export interface DiffHunk {
  kind: "equal" | "delete" | "insert";
  text: string;
}

export function tokenize(text: string): string[] {
  return text.match(/\w+|\s+|[^\w\s]/g) ?? [];
}

/**
 * Word-level diff turning `original` into `suggested`, mirroring the backend's
 * deterministic diff.  Uses a DP longest-common-subsequence so the same input
 * always produces the same hunks.
 */
export function diffWords(original: string, suggested: string): DiffHunk[] {
  const left = tokenize(original);
  const right = tokenize(suggested);
  const n = left.length;
  const m = right.length;

  const dp: number[][] = Array.from({ length: n + 1 }, () =>
    new Array<number>(m + 1).fill(0),
  );
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      dp[i][j] =
        left[i] === right[j]
          ? dp[i + 1][j + 1] + 1
          : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }

  const hunks: DiffHunk[] = [];
  const push = (kind: DiffHunk["kind"], text: string) => {
    if (!text) return;
    const last = hunks[hunks.length - 1];
    if (last && last.kind === kind) last.text += text;
    else hunks.push({ kind, text });
  };

  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (left[i] === right[j]) {
      push("equal", left[i]);
      i++;
      j++;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      push("delete", left[i]);
      i++;
    } else {
      push("insert", right[j]);
      j++;
    }
  }
  while (i < n) {
    push("delete", left[i]);
    i++;
  }
  while (j < m) {
    push("insert", right[j]);
    j++;
  }
  return hunks;
}
