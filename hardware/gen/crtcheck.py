from board import *
from design import PARTS
refs=list(PARTS)
bad=[]
for i,a in enumerate(refs):
    A=courtyard(a)
    if A[0]<BX1+0.3 or A[1]<BY1+0.3 or A[2]>BX2-0.2 or A[3]>BY2-0.3: bad.append(("edge",a,A))
    for b in refs[i+1:]:
        B=courtyard(b)
        ox=min(A[2],B[2])-max(A[0],B[0]); oy=min(A[3],B[3])-max(A[1],B[1])
        if ox>0.001 and oy>0.001: bad.append((a,b,round(ox,2),round(oy,2)))
for x in bad: print(x)
print(len(bad),"issues")
