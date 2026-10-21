"""Independent, student-style solutions (read stdin, print answer). Used to prove every problem's tests are correct in the real sandbox."""
PY = {
"two-sum": """import sys
d=sys.stdin.read().split('\\n'); arr=list(map(int,d[1].split())); t=int(d[2]); seen={}
for j,v in enumerate(arr):
    if t-v in seen: print(seen[t-v],j); break
    seen[v]=j
""",
"valid-parentheses": """s=input().strip(); st=[]; p={')':'(',']':'[','}':'{'}; ok=True
for c in s:
    if c in '([{': st.append(c)
    elif not st or st.pop()!=p[c]: ok=False; break
print('true' if ok and not st else 'false')
""",
"max-subarray": """import sys
d=sys.stdin.read().split('\\n'); a=list(map(int,d[1].split())); best=cur=a[0]
for x in a[1:]:
    cur=max(x,cur+x); best=max(best,cur)
print(best)
""",
"first-unique-char": """from collections import Counter
s=input().strip(); c=Counter(s); print(next((i for i,ch in enumerate(s) if c[ch]==1),-1))
""",
"valid-anagram": """import sys
a,b=sys.stdin.read().split('\\n')[:2]; print('true' if sorted(a.strip())==sorted(b.strip()) else 'false')
""",
"merge-sorted": """import sys
d=sys.stdin.read().split('\\n'); a=list(map(int,d[1].split())); b=list(map(int,d[3].split())); i=j=0; out=[]
while i<len(a) and j<len(b):
    if a[i]<=b[j]: out.append(a[i]); i+=1
    else: out.append(b[j]); j+=1
out+=a[i:]+b[j:]; print(' '.join(map(str,out)))
""",
"binary-search": """import sys
d=sys.stdin.read().split('\\n'); a=list(map(int,d[1].split())); t=int(d[2]); lo,hi=0,len(a)-1; ans=-1
while lo<=hi:
    m=(lo+hi)//2
    if a[m]==t: ans=m; break
    if a[m]<t: lo=m+1
    else: hi=m-1
print(ans)
""",
"climbing-stairs": """n=int(input()); a,b=1,1
for _ in range(n): a,b=b,a+b
print(a)
""",
"longest-substring": """s=input().strip(); last={}; start=best=0
for i,c in enumerate(s):
    if c in last and last[c]>=start: start=last[c]+1
    last[c]=i; best=max(best,i-start+1)
print(best)
""",
"kth-largest": """import sys,heapq
d=sys.stdin.read().split('\\n'); n,k=map(int,d[0].split()); print(heapq.nlargest(k,map(int,d[1].split()))[-1])
""",
"coin-change": """import sys
d=sys.stdin.read().split('\\n'); n,amt=map(int,d[0].split()); coins=list(map(int,d[1].split())); INF=10**9; dp=[0]+[INF]*amt
for a in range(1,amt+1):
    for c in coins:
        if c<=a and dp[a-c]+1<dp[a]: dp[a]=dp[a-c]+1
print(dp[amt] if dp[amt]<INF else -1)
""",
"number-of-islands": """import sys
sys.setrecursionlimit(10**6)
d=sys.stdin.read().split('\\n'); R,C=map(int,d[0].split()); g=[list(d[1+i].strip()) for i in range(R)]; cnt=0
for i in range(R):
    for j in range(C):
        if g[i][j]=='1':
            cnt+=1; st=[(i,j)]; g[i][j]='0'
            while st:
                x,y=st.pop()
                for a,b in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
                    if 0<=a<R and 0<=b<C and g[a][b]=='1': g[a][b]='0'; st.append((a,b))
print(cnt)
""",
}
JS_TWO_SUM = """const L=require('fs').readFileSync(0,'utf8').split('\\n');const a=L[1].split(' ').map(Number),t=+L[2];const m=new Map();
for(let j=0;j<a.length;j++){if(m.has(t-a[j])){console.log(m.get(t-a[j])+' '+j);break;}m.set(a[j],j);}"""
JAVA_TWO_SUM = """import java.util.*;
public class Main { public static void main(String[] x){ Scanner s=new Scanner(System.in); int n=s.nextInt(); int[] a=new int[n]; for(int i=0;i<n;i++)a[i]=s.nextInt(); int t=s.nextInt();
 Map<Integer,Integer> m=new HashMap<>(); for(int j=0;j<n;j++){ if(m.containsKey(t-a[j])){System.out.println(m.get(t-a[j])+" "+j);return;} m.put(a[j],j);} } }"""
