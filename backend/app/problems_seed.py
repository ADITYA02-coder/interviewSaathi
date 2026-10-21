"""Built-in coding problems. Every problem is stdin -> stdout (works in Python, JavaScript and Java).
Expected outputs are produced by the reference solutions below, so the test data can never disagree with the statement."""
import random


def _ints(xs):
    return " ".join(str(x) for x in xs)


# ------------------------------------------------------------------ reference solutions + test generators
def two_sum_ref(inp):
    n, arr, target = int(inp[0]), list(map(int, inp[1].split())), int(inp[2])
    seen = {}
    for j, v in enumerate(arr):
        if target - v in seen:
            return f"{seen[target - v]} {j}"
        seen[v] = j


def two_sum_gen(r):
    out = ["4\n2 7 11 15\n9", "3\n3 2 4\n6", "2\n-3 3\n0", "5\n1 5 9 14 20\n23"]
    while len(out) < 10:
        n = r.randint(2, 60 if len(out) < 8 else 800)
        arr = r.sample(range(-5000, 5000), n)
        i, j = sorted(r.sample(range(n), 2))
        t = arr[i] + arr[j]
        if sum(1 for a in range(n) for b in range(a + 1, n) if arr[a] + arr[b] == t) == 1 if n <= 120 else True:
            if n > 120:
                pairs = {}
                ok = True
                for v in arr:
                    pairs[v] = 1
                cnt = sum(1 for v in arr if (t - v) in pairs and t - v != v) // 2
                ok = cnt == 1
                if not ok:
                    continue
            out.append(f"{n}\n{_ints(arr)}\n{t}")
    return out


def parens_ref(inp):
    st, pair = [], {")": "(", "]": "[", "}": "{"}
    for ch in inp[0].strip():
        if ch in "([{":
            st.append(ch)
        elif not st or st.pop() != pair[ch]:
            return "false"
    return "false" if st else "true"


def parens_gen(r):
    out = ["()[]{}", "(]", "([{}])", "((", "}", "{[()()]}", "([)]", "(((((((((())))))))))"]
    for _ in range(4):
        s = "".join(r.choice("()[]{}") for _ in range(r.randint(2, 40)))
        out.append(s)
    out.append("()" * 5000)
    return out


def kadane_ref(inp):
    arr = list(map(int, inp[1].split()))
    best = cur = arr[0]
    for v in arr[1:]:
        cur = max(v, cur + v)
        best = max(best, cur)
    return str(best)


def kadane_gen(r):
    out = ["9\n-2 1 -3 4 -1 2 1 -5 4", "1\n5", "3\n-3 -1 -2", "5\n5 4 -1 7 8"]
    for k in range(6):
        n = r.randint(1, 40 if k < 4 else 20000)
        out.append(f"{n}\n{_ints(r.randint(-100, 100) for _ in range(n))}")
    return out


def first_unique_ref(inp):
    s = inp[0].strip()
    for i, c in enumerate(s):
        if s.count(c) == 1:
            return str(i)
    return "-1"


def first_unique_gen(r):
    out = ["leetcode", "loveleetcode", "aabb", "z", "abcabcabcd"]
    for k in range(5):
        n = r.randint(3, 30 if k < 3 else 5000)
        out.append("".join(r.choice("abcdefgh" if k % 2 else "abcdefghijklmnopqrstuvwxyz") for _ in range(n)))
    return out


def anagram_ref(inp):
    return "true" if sorted(inp[0].strip()) == sorted(inp[1].strip()) else "false"


def anagram_gen(r):
    out = ["listen\nsilent", "rat\ncar", "a\na", "ab\nabc", "aabbcc\nabcabc", "hello\nbillion"]
    for k in range(4):
        s = [r.choice("abcdef") for _ in range(r.randint(2, 30 if k < 2 else 4000))]
        t = s[:]
        r.shuffle(t)
        if k % 2:
            t[0] = "z"
        out.append("".join(s) + "\n" + "".join(t))
    return out


def merge_ref(inp):
    a = list(map(int, inp[1].split())) if inp[1].strip() else []
    b = list(map(int, inp[3].split())) if inp[3].strip() else []
    return _ints(sorted(a + b))


def merge_gen(r):
    out = ["3\n1 3 5\n3\n2 4 6", "1\n1\n1\n1", "4\n-5 -1 0 10\n2\n-3 8", "2\n1 2\n3\n3 4 5"]
    for k in range(5):
        n, m = r.randint(1, 20 if k < 3 else 3000), r.randint(1, 20 if k < 3 else 3000)
        out.append(f"{n}\n{_ints(sorted(r.randint(-1000, 1000) for _ in range(n)))}\n{m}\n{_ints(sorted(r.randint(-1000, 1000) for _ in range(m)))}")
    return out


def longest_sub_ref(inp):
    s, best, start, last = inp[0].strip(), 0, 0, {}
    for i, c in enumerate(s):
        if c in last and last[c] >= start:
            start = last[c] + 1
        last[c] = i
        best = max(best, i - start + 1)
    return str(best)


def longest_sub_gen(r):
    out = ["abcabcbb", "bbbbb", "pwwkew", "a", "abcdef", "dvdf", "tmmzuxt"]
    for k in range(4):
        out.append("".join(r.choice("abcdefghij" if k % 2 else "abcdefghijklmnopqrstuvwxyz") for _ in range(r.randint(5, 40 if k < 2 else 20000))))
    return out


def bsearch_ref(inp):
    arr, t = list(map(int, inp[1].split())), int(inp[2])
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == t:
            return str(mid)
        lo, hi = (mid + 1, hi) if arr[mid] < t else (lo, mid - 1)
    return "-1"


def bsearch_gen(r):
    out = ["6\n-1 0 3 5 9 12\n9", "6\n-1 0 3 5 9 12\n2", "1\n7\n7", "1\n7\n3"]
    for k in range(6):
        n = r.randint(1, 30 if k < 3 else 20000)
        arr = sorted(r.sample(range(-10**6, 10**6), n))
        t = r.choice(arr) if k % 2 == 0 else r.randint(-10**6, 10**6) | 1
        if k % 2 == 1 and t in arr:
            t += 1
        out.append(f"{n}\n{_ints(arr)}\n{t}")
    return out


def stairs_ref(inp):
    n = int(inp[0])
    a, b = 1, 1
    for _ in range(n):
        a, b = b, a + b
    return str(a)


def stairs_gen(r):
    return ["1", "2", "3", "5", "10", "20", "35", "45", "44", "30"]


def islands_ref(inp):
    R, C = map(int, inp[0].split())
    g = [list(inp[1 + i].strip()) for i in range(R)]
    seen, cnt = set(), 0
    for i in range(R):
        for j in range(C):
            if g[i][j] == "1" and (i, j) not in seen:
                cnt += 1
                st = [(i, j)]
                seen.add((i, j))
                while st:
                    x, y = st.pop()
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        a, b = x + dx, y + dy
                        if 0 <= a < R and 0 <= b < C and g[a][b] == "1" and (a, b) not in seen:
                            seen.add((a, b)); st.append((a, b))
    return str(cnt)


def islands_gen(r):
    out = ["4 5\n11110\n11010\n11000\n00000", "3 5\n11000\n11000\n00100", "1 1\n1", "1 1\n0", "2 2\n10\n01"]
    for k in range(5):
        R, C = r.randint(2, 8 if k < 3 else 200), r.randint(2, 8 if k < 3 else 200)
        p = r.choice([0.3, 0.5, 0.7])
        out.append(f"{R} {C}\n" + "\n".join("".join("1" if r.random() < p else "0" for _ in range(C)) for _ in range(R)))
    return out


def coins_ref(inp):
    n, amount = map(int, inp[0].split())
    coins = list(map(int, inp[1].split()))
    dp = [0] + [10**9] * amount
    for a in range(1, amount + 1):
        for c in coins:
            if c <= a:
                dp[a] = min(dp[a], dp[a - c] + 1)
    return str(dp[amount] if dp[amount] < 10**9 else -1)


def coins_gen(r):
    out = ["3 11\n1 2 5", "1 3\n2", "1 0\n1", "3 6\n1 3 4", "2 7\n2 4", "4 100\n1 5 10 25"]
    for k in range(4):
        n = r.randint(1, 5)
        out.append(f"{n} {r.randint(1, 300 if k < 2 else 5000)}\n{_ints(r.sample(range(1, 60), n))}")
    return out


def kth_ref(inp):
    n, k = map(int, inp[0].split())
    return str(sorted(map(int, inp[1].split()), reverse=True)[k - 1])


def kth_gen(r):
    out = ["6 2\n3 2 1 5 6 4", "9 4\n3 2 3 1 2 4 5 5 6", "1 1\n7", "5 5\n5 4 3 2 1"]
    for k in range(5):
        n = r.randint(2, 30 if k < 3 else 20000)
        out.append(f"{n} {r.randint(1, n)}\n{_ints(r.randint(-10**5, 10**5) for _ in range(n))}")
    return out


def _kw(*pairs):
    return [[label, list(syns)] for label, syns in pairs]


PROBLEMS = [
    dict(id="two-sum", title="Two Sum", difficulty="easy", topic="Arrays and Hashing", ref=two_sum_ref, gen=two_sum_gen, time="O(n)", space="O(n)",
         summary="Given a list of numbers and a target, find the two positions whose values add up to the target.",
         statement="You are given an array of distinct integers and a target. Exactly one pair of different positions has values that add up to the target. Print the two 0-based indices, smaller first.",
         input_format="Line 1: n (the array length)\nLine 2: n space-separated integers\nLine 3: the target", output_format="Two indices i and j (i < j) separated by a space",
         approach=_kw(("a hash map of seen values", ["hash", "dictionary", "map", "dict"]), ("checking the complement of each number", ["complement", "target minus", "target -", "difference"]), ("doing it in a single pass", ["one pass", "single pass", "once"]))),
    dict(id="valid-parentheses", title="Valid Parentheses", difficulty="easy", topic="Stacks", ref=parens_ref, gen=parens_gen, time="O(n)", space="O(n)",
         summary="Given a string of brackets, decide whether every bracket is closed in the right order.",
         statement="A string made only of the characters ()[]{} is valid if every opening bracket is closed by the same type of bracket, in the correct order. Print true if the string is valid, otherwise false.",
         input_format="One line: the bracket string", output_format="true or false",
         approach=_kw(("a stack", ["stack"]), ("pushing opening brackets and popping on closing ones", ["push", "pop"]), ("matching the bracket types", ["match", "same type", "corresponding"]), ("checking the stack is empty at the end", ["empty at the end", "leftover", "remaining"]))),
    dict(id="max-subarray", title="Maximum Subarray", difficulty="easy", topic="Dynamic Programming", ref=kadane_ref, gen=kadane_gen, time="O(n)", space="O(1)",
         summary="Find the contiguous stretch of an array with the largest sum.",
         statement="Given an array of integers (it may contain negatives), find the contiguous non-empty subarray with the largest sum and print that sum.",
         input_format="Line 1: n\nLine 2: n space-separated integers", output_format="One integer: the maximum subarray sum",
         approach=_kw(("Kadane's algorithm", ["kadane"]), ("a running sum that resets when it goes negative", ["running", "current sum", "reset", "restart"]), ("tracking the best sum so far", ["best", "maximum so far", "global max", "max so far"]))),
    dict(id="first-unique-char", title="First Unique Character", difficulty="easy", topic="Strings", ref=first_unique_ref, gen=first_unique_gen, time="O(n)", space="O(1)",
         summary="Find the position of the first character that appears only once in a string.",
         statement="Given a lowercase string, print the 0-based index of the first character that appears exactly once. Print -1 if there is none.",
         input_format="One line: the string", output_format="One integer: the index, or -1",
         approach=_kw(("counting each character", ["count", "frequency", "freq", "hash", "map", "array of 26"]), ("a second pass to find the first character with count one", ["second pass", "again", "two pass", "iterate again", "loop again"]))),
    dict(id="valid-anagram", title="Valid Anagram", difficulty="easy", topic="Strings", ref=anagram_ref, gen=anagram_gen, time="O(n)", space="O(1)",
         summary="Check whether two words are made of exactly the same letters.",
         statement="Two strings are anagrams if one can be rearranged into the other. Print true if they are anagrams, otherwise false.",
         input_format="Line 1: the first string\nLine 2: the second string", output_format="true or false",
         approach=_kw(("comparing letter counts", ["count", "frequency", "hash", "map"]), ("sorting both strings and comparing", ["sort"]), ("checking the lengths first", ["length"]))),
    dict(id="merge-sorted", title="Merge Two Sorted Arrays", difficulty="easy", topic="Two Pointers", ref=merge_ref, gen=merge_gen, time="O(n + m)", space="O(n + m)",
         summary="Merge two already sorted lists into one sorted list.",
         statement="Given two arrays sorted in non-decreasing order, print them merged into a single sorted array.",
         input_format="Line 1: n\nLine 2: n sorted integers\nLine 3: m\nLine 4: m sorted integers", output_format="n + m integers in sorted order, separated by spaces",
         approach=_kw(("two pointers", ["two pointer", "two pointers", "pointer", "index"]), ("comparing the front elements", ["compare", "smaller"]), ("copying the leftovers", ["leftover", "remaining", "rest"]))),
    dict(id="binary-search", title="Binary Search", difficulty="easy", topic="Searching", ref=bsearch_ref, gen=bsearch_gen, time="O(log n)", space="O(1)",
         summary="Find a number in a sorted array in logarithmic time.",
         statement="Given an array sorted in increasing order and a target, print the index of the target, or -1 if it is not present. Your solution should run in O(log n).",
         input_format="Line 1: n\nLine 2: n sorted distinct integers\nLine 3: target", output_format="The index, or -1",
         approach=_kw(("halving the search range", ["half", "middle", "mid", "divide"]), ("low and high pointers", ["low", "high", "left", "right"]), ("the fact that the array is sorted", ["sorted"]))),
    dict(id="climbing-stairs", title="Climbing Stairs", difficulty="easy", topic="Dynamic Programming", ref=stairs_ref, gen=stairs_gen, time="O(n)", space="O(1)",
         summary="Count the ways to climb a staircase taking one or two steps at a time.",
         statement="You climb a staircase with n steps, taking 1 or 2 steps at a time. Print the number of distinct ways to reach the top.",
         input_format="One integer n (1 <= n <= 45)", output_format="One integer: the number of ways",
         approach=_kw(("the recurrence ways(n) = ways(n-1) + ways(n-2)", ["n-1", "n - 1", "previous two", "last two", "fibonacci", "recurrence"]), ("dynamic programming or memoization", ["dynamic", "dp", "memo"]), ("keeping only the last two values", ["two variables", "last two", "constant space"]))),
    dict(id="longest-substring", title="Longest Substring Without Repeating Characters", difficulty="medium", topic="Sliding Window", ref=longest_sub_ref, gen=longest_sub_gen, time="O(n)", space="O(k)",
         summary="Find the length of the longest stretch of a string with no repeated characters.",
         statement="Given a string, print the length of the longest substring that contains no repeated characters.",
         input_format="One line: the string", output_format="One integer: the length",
         approach=_kw(("a sliding window", ["sliding window", "window"]), ("a set or map of last seen positions", ["set", "map", "hash", "last seen", "dictionary"]), ("moving the left edge when a repeat appears", ["left", "start", "shrink", "move"]))),
    dict(id="kth-largest", title="Kth Largest Element", difficulty="medium", topic="Heaps and Sorting", ref=kth_ref, gen=kth_gen, time="O(n log k)", space="O(k)",
         summary="Find the kth largest number in an unsorted array.",
         statement="Given an unsorted array and an integer k, print the kth largest element (counting duplicates, so the 2nd largest of 5 5 4 is 5).",
         input_format="Line 1: n and k\nLine 2: n integers", output_format="One integer",
         approach=_kw(("sorting and indexing", ["sort"]), ("a min-heap of size k", ["heap", "priority queue", "min heap", "min-heap"]), ("quickselect", ["quickselect", "quick select", "partition"]))),
    dict(id="coin-change", title="Coin Change", difficulty="medium", topic="Dynamic Programming", ref=coins_ref, gen=coins_gen, time="O(amount x coins)", space="O(amount)",
         summary="Find the fewest coins needed to make an amount.",
         statement="Given coin denominations (unlimited supply of each) and a target amount, print the fewest coins needed to make the amount exactly, or -1 if it is impossible. An amount of 0 needs 0 coins.",
         input_format="Line 1: n (number of coin types) and the amount\nLine 2: the n coin values", output_format="One integer",
         approach=_kw(("dynamic programming over amounts", ["dynamic", "dp", "table", "array"]), ("dp[a] as one plus the minimum over the coins", ["min", "minimum", "fewest"]), ("why greedy does not always work", ["greedy"]), ("marking unreachable amounts as infinite", ["infinity", "impossible", "-1", "unreachable"]))),
    dict(id="number-of-islands", title="Number of Islands", difficulty="medium", topic="Graphs", ref=islands_ref, gen=islands_gen, time="O(rows x cols)", space="O(rows x cols)",
         summary="Count the separate islands of land in a grid.",
         statement="A grid contains 1 (land) and 0 (water). An island is a group of land cells connected horizontally or vertically. Print the number of islands.",
         input_format="Line 1: rows and cols\nNext rows lines: a string of cols characters, each 0 or 1", output_format="One integer",
         approach=_kw(("DFS or BFS flood fill", ["dfs", "bfs", "depth", "breadth", "flood"]), ("marking visited cells", ["visited", "mark", "seen", "sink"]), ("counting each new start", ["count"]), ("the four directions", ["four", "up down", "neighbors", "neighbours", "directions"]))),
]


def build_rows():
    """Yield Problem kwargs with tests generated from the reference solutions."""
    for p in PROBLEMS:
        r = random.Random(p["id"])
        inputs = p["gen"](r)
        tests = []
        for i, raw in enumerate(inputs):
            lines = raw.split("\n")
            tests.append({"input": raw + "\n", "expected": p["ref"](lines), "hidden": i >= 2})
        examples = [{"input": t["input"].strip(), "output": t["expected"]} for t in tests[:2]]
        yield dict(id=p["id"], title=p["title"], difficulty=p["difficulty"], topic=p["topic"], statement=p["statement"], input_format=p["input_format"],
                   output_format=p["output_format"], examples=examples, tests=tests, expected_time=p["time"], expected_space=p["space"],
                   approach_keywords=p["approach"], summary=p["summary"], active=True, source="builtin")


def seed(db):
    from .db import Problem
    have = {x for (x,) in db.query(Problem.id).all()}
    for row in build_rows():
        if row["id"] not in have:
            db.add(Problem(**row))
    db.commit()
