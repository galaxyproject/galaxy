"""
Topological sort.

From Tim Peters, see:
   http://mail.python.org/pipermail/python-list/1999-July/006660.html

topsort takes a list of pairs, where each pair (x, y) is taken to
mean that x <= y wrt some abstract partial ordering.  The return
value is a list, representing a total ordering that respects all
the input constraints.
E.g.,

   topsort( [(1,2), (3,3)] )

Valid topological sorts would be any of (but nothing other than)

   [3, 1, 2]
   [1, 3, 2]
   [1, 2, 3]

... however this variant ensures that 'key' order (first element of
tuple) is preserved so the following will be result returned:

   [1, 3, 2]

because those are the permutations of the input elements that
respect the "1 precedes 2" and "3 precedes 3" input constraints.
Note that a constraint of the form (x, x) is really just a trick
to make sure x appears *somewhere* in the output list.

If there's a cycle in the constraints, say

   topsort( [(1,2), (2,1)] )

then CycleError is raised, and the exception object supports
many methods to help analyze and break the cycles.  This requires
a good deal more code than topsort itself!
"""


class CycleError(Exception):
    def __init__(self, sofar, numpreds, succs):
        Exception.__init__(self, "cycle in constraints",
                           sofar, numpreds, succs)
        self.preds = None

    # return as much of the total ordering as topsort was able to
    # find before it hit a cycle
    def get_partial(self):
        return self[1]

    # return remaining elt -> count of predecessors map
    def get_pred_counts(self):
        return self[2]

    # return remaining elt -> list of successors map
    def get_succs(self):
        return self[3]

    # return remaining elements (== those that don't appear in
    # get_partial())
    def get_elements(self):
        return self.get_pred_counts().keys()

    # Return a list of pairs representing the full state of what's
    # remaining (if you pass this list back to topsort, it will raise
    # CycleError again, and if you invoke get_pairlist on *that*
    # exception object, the result will be isomorphic to *this*
    # invocation of get_pairlist).
    # The idea is that you can use pick_a_cycle to find a cycle,
    # through some means or another pick an (x,y) pair in the cycle
    # you no longer want to respect, then remove that pair from the
    # output of get_pairlist and try topsort again.
    def get_pairlist(self):
        succs = self.get_succs()
        answer = []
        for x in self.get_elements():
            if x in succs:
                for y in succs[x]:
                    answer.append((x, y))
            else:
                # make sure x appears in topsort's output!
                answer.append((x, x))
        return answer

    # return remaining elt -> list of predecessors map
    def get_preds(self):
        if self.preds is not None:
            return self.preds
        self.preds = preds = {}
        remaining_elts = self.get_elements()
        for x in remaining_elts:
            preds[x] = []
        succs = self.get_succs()

        for x in remaining_elts:
            if x in succs:
                for y in succs[x]:
                    preds[y].append(x)

        if __debug__:
            for x in remaining_elts:
                assert len(preds[x]) > 0
        return preds

    # return a cycle [x, ..., x] at random
    def pick_a_cycle(self):
        remaining_elts = self.get_elements()

        # We know that everything in remaining_elts has a predecessor,
        # but don't know that everything in it has a successor.  So
        # crawling forward over succs may hit a dead end.  Instead we
        # crawl backward over the preds until we hit a duplicate, then
        # reverse the path.
        preds = self.get_preds()
        from random import choice
        x = choice(remaining_elts)
        answer = []
        index = {}
        in_answer = index.has_key
        while not in_answer(x):
            index[x] = len(answer)  # index of x in answer
            answer.append(x)
            x = choice(preds[x])
        answer.append(x)
        answer = answer[index[x]:]
        answer.reverse()
        return answer


def _numpreds_and_successors_from_pairlist(pairlist):
    numpreds = {}   # elt -> # of predecessors
    successors = {}  # elt -> list of successors
    for first, second in pairlist:
        # make sure every elt is a key in numpreds
        if first not in numpreds:
            numpreds[first] = 0
        if second not in numpreds:
            numpreds[second] = 0

        # if they're the same, there's no real dependence
        if first == second:
            continue

        # since first < second, second gains a pred ...
        numpreds[second] = numpreds[second] + 1

        # ... and first gains a succ
        if first in successors:
            successors[first].append(second)
        else:
            successors[first] = [second]
    return numpreds, successors


def topsort(pairlist):
    numpreds, successors = _numpreds_and_successors_from_pairlist(pairlist)

    # suck up everything without a predecessor
    answer = [x for x in numpreds.keys() if numpreds[x] == 0]

    # for everything in answer, knock down the pred count on
    # its successors; note that answer grows *in* the loop
    for x in answer:
        assert numpreds[x] == 0
        del numpreds[x]
        if x in successors:
            for y in successors[x]:
                numpreds[y] = numpreds[y] - 1
                if numpreds[y] == 0:
                    answer.append(y)
            # following "del" isn't needed; just makes
            # CycleError details easier to grasp
            del successors[x]

    if numpreds:
        # everything in numpreds has at least one predecessor ->
        # there's a cycle
        if __debug__:
            for x in numpreds.keys():
                assert numpreds[x] > 0
        raise CycleError(answer, numpreds, successors)
    return answer


def topsort_levels(pairlist):
    numpreds, successors = _numpreds_and_successors_from_pairlist(pairlist)

    answer = []

    while 1:
        # Suck up everything without a predecessor.
        levparents = [x for x in numpreds.keys() if numpreds[x] == 0]
        if not levparents:
            break
        answer.append(levparents)
        for levparent in levparents:
            del numpreds[levparent]
            if levparent in successors:
                for levparentsucc in successors[levparent]:
                    numpreds[levparentsucc] -= 1
                del successors[levparent]

    if numpreds:
        # Everything in num_parents has at least one child ->
        # there's a cycle.
        raise CycleError(answer, numpreds, successors)

    return answer
