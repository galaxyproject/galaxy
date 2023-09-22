"""
Functions for working with SAM/BAM CIGAR representation.
"""

import operator


def get_ref_based_read_seq_and_cigar(read_seq, read_start, ref_seq, ref_seq_start, cigar):
    """
    Returns a ( new_read_seq, new_cigar ) that can be used with reference
    sequence to reconstruct the read. The new read sequence includes only
    bases that cannot be recovered from the reference: mismatches and
    insertions (soft clipped bases are not included). The new cigar replaces
    Ms with =s and Xs because the M operation can denote a sequence match or
    mismatch.
    """

    if not ref_seq:
        return read_seq, cigar

    # Set up position for reference, read.
    ref_seq_pos = read_start - ref_seq_start
    read_pos = 0

    # Create new read sequence, cigar.
    new_read_seq = ""
    new_cigar = ""
    cigar_ops = "MIDNSHP=X"
    for op_tuple in cigar:
        op, op_len = op_tuple
        # Op is index into string 'MIDNSHP=X'
        if op == 0:  # Match
            # Transform Ms to =s and Xs using reference.
            new_op = ""
            total_count = 0
            while total_count < op_len and ref_seq_pos < len(ref_seq):
                match, count = _match_mismatch_counter(read_seq, read_pos, ref_seq, ref_seq_pos)
                # Use min because count cannot exceed remainder of operation.
                count = min(count, op_len - total_count)
                if match:
                    new_op = "="
                else:
                    new_op = "X"
                    # Include mismatched bases in new read sequence.
                    new_read_seq += read_seq[read_pos : read_pos + count]
                new_cigar += "%i%s" % (count, new_op)
                total_count += count
                read_pos += count
                ref_seq_pos += count

            # If end of read falls outside of ref_seq data, leave as M.
            if total_count < op_len:
                new_cigar += "%iM" % (op_len - total_count)
        elif op == 1:  # Insertion
            new_cigar += "%i%s" % (op_len, cigar_ops[op])
            # Include insertion bases in new read sequence.
            new_read_seq += read_seq[read_pos : read_pos + op_len]
            read_pos += op_len
        elif op in [2, 3, 6]:  # Deletion, Skip, or Padding
            ref_seq_pos += op_len
            new_cigar += "%i%s" % (op_len, cigar_ops[op])
        elif op == 4:  # Soft clipping
            read_pos += op_len
            new_cigar += "%i%s" % (op_len, cigar_ops[op])
        elif op == 5:  # Hard clipping
            new_cigar += "%i%s" % (op_len, cigar_ops[op])
        elif op in [7, 8]:  # Match or mismatch
            if op == 8:
                # Include mismatched bases in new read sequence.
                new_read_seq += read_seq[read_pos : read_pos + op_len]
            read_pos += op_len
            ref_seq_pos += op_len
            new_cigar += "%i%s" % (op_len, cigar_ops[op])

    return (new_read_seq, new_cigar)


def _match_mismatch_counter(s1, p1, s2, p2):
    """
    Count consecutive matches/mismatches between strings s1 and s2
    starting at p1 and p2, respectively.
    """

    # Do initial comparison to determine whether to count matches or
    # mismatches.
    if s1[p1] == s2[p2]:
        cmp_fn = operator.eq
        match = True
    else:
        cmp_fn = operator.ne
        match = False

    # Increment counts to move to next characters.
    count = 1
    p1 += 1
    p2 += 1

    # Count matches/mismatches.
    while p1 < len(s1) and p2 < len(s2) and cmp_fn(s1[p1], s2[p2]):
        count += 1
        p1 += 1
        p2 += 1

    return match, count
