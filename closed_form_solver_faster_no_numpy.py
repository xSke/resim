import itertools
import struct

# original code by ubuntor: https://discord.com/channels/738107179294523402/875833188537208842/965050266258903070

MASK = 0xFFFFFFFFFFFFFFFF
BRUTEFORCE_THRESHOLD = 2**20


def powerset(s):
    return itertools.chain.from_iterable(itertools.combinations(s, r) for r in range(len(s) + 1))


def lshift_var(a, n):
    return a[n:] + [0] * n


def rshift_var(a, n):
    return [0] * n + a[:-n]


def xor_var(a, b):
    return [x ^ y for x, y in zip(a, b)]


def init_sym():
    state0 = [0] * 64
    state1 = [0] * 64
    for i in range(64):
        state0[i] = 1 << (127 - i)
        state1[i] = 1 << (127 - (64 + i))
    return state0, state1


def rref(mat, n):
    m = len(mat)
    mat = mat[:]
    next_row = 0
    for col in range(n):
        for row in range(next_row, m):
            if (mat[row] >> (n - 1 - col)) & 1 == 1:
                mat[row], mat[next_row] = mat[next_row], mat[row]
                for i in range(m):
                    if i != next_row and (mat[i] >> (n - 1 - col)) & 1 == 1:
                        mat[i] ^= mat[next_row]
                next_row += 1
                if next_row == m:
                    return mat
                break
    return mat


def transpose(mat):
    n = len(mat)
    r = [0] * 128
    for i in range(128):
        s = 0
        for j in range(n):
            s += ((mat[j] >> (127 - i)) & 1) << (n - 1 - j)
        r[i] = s
    return r


def xs128p_sym(state0, state1):
    state0 = state0[:]
    state1 = state1[:]
    s1, s0 = state0, state1
    s1 = xor_var(s1, lshift_var(s1, 23))
    s1 = xor_var(s1, rshift_var(s1, 17))
    s1 = xor_var(s1, s0)
    s1 = xor_var(s1, rshift_var(s0, 26))
    state0 = state1
    state1 = s1
    return state0, state1


def xs128p(state0, state1):
    s1 = state0 & MASK
    s0 = state1 & MASK
    s1 ^= (s1 << 23) & MASK
    s1 ^= (s1 >> 17) & MASK
    s1 ^= s0 & MASK
    s1 ^= (s0 >> 26) & MASK
    state0 = state1 & MASK
    state1 = s1 & MASK
    return state0, state1


def state_to_double(s0):
    double_bits = (s0 >> 12) | 0x3FF0000000000000
    return struct.unpack("d", struct.pack("<Q", double_bits))[0] - 1


def get_mantissa(val):
    if val == 1.0:
        return MASK >> 12
    return struct.unpack("<Q", struct.pack("d", val + 1))[0] & 0x000FFFFFFFFFFFFF


def int_to_bits(n, length):
    return [(n >> (length - i - 1)) & 1 for i in range(length)]


def bits_to_int(bits):
    return int("".join(str(i) for i in bits), 2)


def print_mat(M, n):
    for row in M:
        print(f"{row:0{n}b}")
    print()


def solve(knowns):
    """knowns: list of
         float             [known value]
      or (float, float)    [known range]
      or None              [no constraint]

    returns list of all possible solutions (s0,s1)
    ([] if no solution found)
    """
    bits_sym = []
    bits = []
    state0_sym, state1_sym = init_sym()

    for known in knowns:
        if type(known) == float:
            mantissa_bits = int_to_bits(get_mantissa(known), 52)
            bits += mantissa_bits
            bits_sym += state0_sym[:52]
        elif type(known) in [tuple, list]:
            lo, hi = known
            lo_mantissa = get_mantissa(lo)
            hi_mantissa = get_mantissa(hi)
            known_bits = 52 - (lo_mantissa ^ hi_mantissa).bit_length()
            bits += int_to_bits(lo_mantissa >> (52 - known_bits), known_bits)
            bits_sym += state0_sym[:known_bits]
        elif known == None:
            pass
        else:
            print("unknown type for known", known)
            1 / 0
        state0_sym, state1_sym = xs128p_sym(state0_sym, state1_sym)

    num_known = len(bits)
    # print('solving...')

    # find kernel basis (homogeneous solutions)
    kernel_basis = []

    M = transpose(bits_sym)

    M = [(M[i] << 128) + (1 << (127 - i)) for i in range(128)]
    M = rref(M, num_known + 128)
    for row in M:
        if row >> 128 == 0:
            kernel_basis.append(row & ((1 << 128) - 1))

    if len(kernel_basis) > 0:
        print(f"WARNING: {2**len(kernel_basis)} (2^{len(kernel_basis)}) potential solutions")
        if 2 ** len(kernel_basis) > BRUTEFORCE_THRESHOLD:
            print("too many to bruteforce, giving up :(")
            return []

    # find particular solution
    M = [(bits_sym[i] << 1) + bits[i] for i in range(len(bits_sym))]
    M = rref(M, 129)

    particular_solution = 0
    for row in M:
        if row == 0:
            break
        if row == 1:
            # print('ERROR: contradiction found, no solution!')
            return []
        particular_solution += (row & 1) << (row.bit_length() - 2)

    solutions = []

    for homogeneous_solutions in powerset(kernel_basis):
        solution = particular_solution
        for vec in homogeneous_solutions:
            solution ^= vec
        s0 = solution >> 64
        s1 = solution & ((1 << 64) - 1)
        candidate_solution = (s0, s1)
        # test solution
        for known in knowns:
            value = state_to_double(s0)
            if type(known) == float:
                if known != value:
                    break
            elif type(known) in [tuple, list]:
                lo, hi = known
                if not (lo < value < hi):
                    break
            s0, s1 = xs128p(s0, s1)
        else:
            # good solution!
            # print('found solution', candidate_solution)
            solutions.append(candidate_solution)
    return solutions
