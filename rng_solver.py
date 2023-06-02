import functools
import itertools
import struct

from typing import Optional, TypedDict, Union

# original code by ubuntor: https://discord.com/channels/738107179294523402/875833188537208842/965050266258903070

# Each state is a 64-bit integer
STATE_WIDTH = 64
# Solution space is two states wide, so 128
SOLUTION_WIDTH = 2 * STATE_WIDTH
# 128x128 identity matrix, precomputed
IDENTITY128 = [1 << (SOLUTION_WIDTH - 1 - i) for i in range(SOLUTION_WIDTH)]
STATE_MASK = int("1" * STATE_WIDTH, 2)
SOLUTION_MASK = STATE_MASK << STATE_WIDTH | STATE_MASK
MAX_KERNEL_BASIS_SIZE = 20

BitMatrix = list[int]
KnownRoll = Union[float, tuple[float, float], None]


@functools.cache
def state_matrices(i: int) -> (BitMatrix, BitMatrix):
    """
    Develop the bit matrices which define state spaces
    """
    if i == 0:
        # As bits, initial state matrices are the top and bottom halves
        # of a 128x128 identity matrix. At a smaller scale they look like this:
        #
        #                  state0              state1
        #
        #                 10000000            00001000
        #                 01000000            00000100
        #                 00100000            00000010
        #                 00010000            00000001
        return IDENTITY128[:STATE_WIDTH], IDENTITY128[STATE_WIDTH:]
    # Otherwise, run Xorshift128+ on the prior set of [cached] states
    return xs128p_matrix(*state_matrices(i - 1))


def xs128p_matrix(state0_matrix: BitMatrix, state1_matrix: BitMatrix) -> tuple[BitMatrix, BitMatrix]:
    """
    Equivalent to Xorshift128+ implementation across matrices of states.
    """
    state0_matrix = state0_matrix[:]
    state1_matrix = state1_matrix[:]
    s1, s0 = state0_matrix, state1_matrix
    s1 = xor_matrix(s1, lshift_matrix(s1, 23))
    s1 = xor_matrix(s1, rshift_matrix(s1, 17))
    s1 = xor_matrix(s1, s0)
    s1 = xor_matrix(s1, rshift_matrix(s0, 26))
    state0_matrix = state1_matrix
    state1_matrix = s1
    return state0_matrix, state1_matrix


def lshift_matrix(matrix: BitMatrix, n: int) -> BitMatrix:
    """
    "left-shift" the bit matrix by sliding it up N rows
    """
    return matrix[n:] + [0] * n


def rshift_matrix(matrix: BitMatrix, n: int) -> BitMatrix:
    """
    "right-shift" the bit matrix by sliding it down N rows
    """
    return [0] * n + matrix[:-n]


def xor_matrix(matrix1: BitMatrix, matrix2: BitMatrix) -> BitMatrix:
    """
    XOR two bit matrices together, row-wise
    """
    result = []
    for i in range(min(len(matrix1), len(matrix2))):
        result.append(matrix1[i] ^ matrix2[i])
    return result


def rref(matrix: BitMatrix, num_cols: int) -> BitMatrix:
    """
    Reduced Row Echelon Form (RREF) of a matrix
    """
    matrix = matrix[:]
    num_rows = len(matrix)
    next_row = 0
    for col in range(num_cols):
        col_bitmask = 1 << (num_cols - 1 - col)
        for row in range(next_row, num_rows):
            if not matrix[row] & col_bitmask:
                continue
            # Flip rows
            matrix[row], matrix[next_row] = matrix[next_row], matrix[row]
            for i in range(num_rows):
                if i == next_row:
                    continue
                # XOR all rows except next row
                if matrix[i] & col_bitmask:
                    matrix[i] ^= matrix[next_row]
            next_row += 1
            if next_row == num_rows:
                return matrix
            break
    return matrix


def transpose(matrix: BitMatrix) -> BitMatrix:
    """
    Transposes a bit matrix.
    Assumes the input matrix is 128 bits wide, so the output is 128 rows tall.
    """
    num_rows = len(matrix)
    flipped = []
    for i in range(SOLUTION_WIDTH):
        cell = 0
        for j in range(num_rows):
            bit = (matrix[j] >> (SOLUTION_WIDTH - 1 - i)) & 1
            cell |= bit << (num_rows - 1 - j)
        flipped.append(cell)
    return flipped


def get_kernel_basis(bits_from_states: BitMatrix) -> BitMatrix:
    """
    Find kernel basis (homogeneous solutions)
    https://en.wikipedia.org/wiki/Kernel_(linear_algebra)#Computation_by_Gaussian_elimination
    """

    # bits_from_states is 128 cols wide and (# known bits) rows tall
    # transpose it to 128 rows tall, and (# known bits) cols wide
    M = transpose(bits_from_states)

    # Augment our matrix from M to [M|I], where I is the 128x128 identity matrix
    for i in range(len(M)):
        # Shifts the matrix left 128 spaces
        M[i] <<= SOLUTION_WIDTH
        # Draws the identity matrix in the righthand side of each row
        M[i] |= IDENTITY128[i]

    # RREF to effectively solve the system of equations
    M = rref(M, len(bits_from_states) + SOLUTION_WIDTH)

    kernel_basis = []
    for row in M:
        if row >> SOLUTION_WIDTH:
            continue
        kernel_basis.append(row & SOLUTION_MASK)

    size = len(kernel_basis)
    if size > 0:
        print(f"WARNING: {2**size} (2^{size}) potential solutions")

    return kernel_basis


def get_particular_solution(
    bits_from_states: BitMatrix,
    bits_from_knowns: list[bool],
) -> Optional[int]:
    """
    Solve for the particular solution based on the bits
    in the states and knowns. If this hits a contradiction
    then there's no solveable solution within the knowns provided.
    """

    # Augment our matrix to [S|K], where S = states and K = knowns
    M = [(row << 1) | bits_from_knowns[i] for i, row in enumerate(bits_from_states)]

    # RREF to effectively solve the system of equations
    # Since S is 128 wide and K is 1 wide, the effective width of M is 129
    M = rref(M, SOLUTION_WIDTH + 1)

    # int holding the 128 bits of the solution
    solution = 0
    for i, row in enumerate(M):
        if row == 0:
            # Reached the rows of the RREF'd matrix which are 0, so stop
            break
        if row == 1:
            # Contradiction found; no solution
            return None
        if row & 1:
            # Otherwise, set the relevant bit in the solution
            solution |= IDENTITY128[1 - row.bit_length()]

    return solution


def powerset(s: list[int]) -> list[tuple[int, ...]]:
    """
    Given [1, 2], returns [(), (1,), (2,), (1, 2)]
    """
    return itertools.chain.from_iterable(itertools.combinations(s, r) for r in range(len(s) + 1))


def xs128p(state0: int, state1: int) -> tuple[int, int]:
    """
    Xorshift128+ implementation
    """
    s1 = state0 & STATE_MASK
    s0 = state1 & STATE_MASK
    s1 ^= (s1 << 23) & STATE_MASK
    s1 ^= (s1 >> 17) & STATE_MASK
    s1 ^= s0 & STATE_MASK
    s1 ^= (s0 >> 26) & STATE_MASK
    state0 = state1 & STATE_MASK
    state1 = s1 & STATE_MASK
    return state0, state1


def xs128p_backward(state0: int, state1: int) -> tuple[int, int]:
    """
    Inverse of Xorshift128+ implementation, steps state backwards by 1
    """
    prev_state1 = state0
    prev_state0 = state1 ^ (state0 >> 26)
    prev_state0 = prev_state0 ^ state0
    prev_state0 = reverse17(prev_state0)
    prev_state0 = reverse23(prev_state0)
    return prev_state0, prev_state1


def reverse17(val: int) -> int:
    return val ^ (val >> 17) ^ (val >> 34) ^ (val >> 51)


def reverse23(val: int) -> int:
    return (val ^ (val << 23) ^ (val << 46)) & STATE_MASK


def state_to_double(s0: int) -> float:
    double_bits = (s0 >> 12) | 0x3FF0000000000000
    return struct.unpack("d", struct.pack("<Q", double_bits))[0] - 1


def get_mantissa(val: float) -> int:
    if val == 1.0:
        return STATE_MASK >> 12
    return struct.unpack("<Q", struct.pack("d", val + 1))[0] & 0x000FFFFFFFFFFFFF


def int_to_bits(n: int, length: int) -> list[bool]:
    return [bool((n >> (length - i - 1)) & 1) for i in range(length)]


def bits_to_int(bits: list[bool]) -> int:
    return int("".join(map(str, map(int, bits))), 2)


def print_matrix(M: BitMatrix, num_cols: int = SOLUTION_WIDTH) -> None:
    for row in M:
        print(f"{row:0{num_cols}b}")
    print()


def solve_in_rng_order(knowns: list[KnownRoll]) -> list[tuple[int, int]]:
    """
    Determine valid RNG states which could output float values matching knowns

    knowns: list of constraints for consecutive RNG float outputs
    Each known can be:
        float               [known value between 0.0 and 1.0]
        (float, float)      [known range of (low, high) values]
        or None             [no constraint for this output]

    Returns list of all possible solutions (s0, s1), or [] if no solution found
    """

    # bits_from_knowns holds the individual bits we are confident in
    # from the knowns provided. It's effectively an 1xN bit matrix
    bits_from_knowns: list[bool] = []
    # bits_from_states holds the complementary bits from the state matrices
    # which we're iterating over as we step to each known. 128xN bit matrix
    bits_from_states: BitMatrix = []

    for i, known in enumerate(knowns):
        state0_matrix, _ = state_matrices(i)
        if type(known) == float:
            mantissa = get_mantissa(known)
            # If the known is a float, then we capture and gain
            # all 52 bits of entropy from that float's mantissa
            num_bits = 52
            # Store all of the mantissa's bits from the knowns
            bits_from_knowns += int_to_bits(mantissa, num_bits)
            # Store all of the bit matrix rows from the states
            bits_from_states += state0_matrix[:num_bits]
        elif type(known) in [tuple, list]:
            lo, hi = known
            lo_mantissa = get_mantissa(lo)
            hi_mantissa = get_mantissa(hi)
            # If the known is a float range, then we capture the high bits
            # which are stable between the mantissae of the range's bounds
            num_bits = 52 - (lo_mantissa ^ hi_mantissa).bit_length()
            # Store those stable high bits from the mantissa of the knowns
            bits_from_knowns += int_to_bits(lo_mantissa >> (52 - num_bits), num_bits)
            # Store the same number of bit matrix rows from the states
            bits_from_states += state0_matrix[:num_bits]
        elif known is None:
            # This is fine, just no bits of info are added
            continue
        else:
            raise TypeError(f"Unknown type '{type(known)}' for known {known}")

    # Find the particular solution, if one exists, of the states and knowns
    particular_solution = get_particular_solution(bits_from_states, bits_from_knowns)
    if particular_solution is None:
        # Contradiction found, no solutions
        return []

    # The kernel basis is a list of bit combos, derived from
    # the state0 matrices, which represent the permutable space
    # of possible homogeneous solutions. If we have enough known bits
    # of information, then the basis will have a small (or even 0)
    # length, and we won't need to check a bunch of permutations
    # beyond the particular solution we just found.
    kernel_basis = get_kernel_basis(bits_from_states)

    if len(kernel_basis) > MAX_KERNEL_BASIS_SIZE:
        print("Too many to bruteforce, giving up :(")
        return []

    # Now to check and save good solutions which satisfy our knowns
    solutions = []

    for homogeneous_solutions in powerset(kernel_basis):
        # Start with the particular solution we found for our states and knowns
        solution = particular_solution
        # Then XOR that particular solution with a permutation of
        # possible homogeneous solutions found in the kernel basis step
        for vec in homogeneous_solutions:
            solution ^= vec

        # Our solution is a 128-bit-wide integer.
        # The high and low 64 bits are s0 & s1, respectively
        s0 = solution >> STATE_WIDTH
        s1 = solution & STATE_MASK
        candidate_solution = (s0, s1)

        # Now test this solution state (s0, s1) against our knowns,
        # iterating the state for each known and comparing the float
        # associated with that state against the known constraints
        for known in knowns:
            value = state_to_double(s0)
            if type(known) == float:
                if known != value:
                    # Floats don't match, try next candidate
                    break
            elif type(known) in [tuple, list]:
                lo, hi = known
                if not (lo < value < hi):
                    # Float outside bounds, try next candidate
                    break
            # Step the state forward to try the next known
            s0, s1 = xs128p(s0, s1)
        else:
            # We did not contradict any of the knowns,
            # so this is a good solution!
            solutions.append(candidate_solution)

    return solutions


BLOCK_SIZE = 64


class RNGStateSolution(TypedDict):
    state: tuple[int, int]
    offset: int
    roll: float
    crossesBlockBoundary: bool


def solve_in_math_random_order(rolls: list[KnownRoll]) -> list[RNGStateSolution]:
    """
    Math.random() generates blocks of 64 values, and then reverses them:

       block 1, roll 63
       block 1, roll 62
       block 1, roll 61
       ...
       block 1, roll  2
       block 1, roll  1
       block 1, roll  0
       block 2, roll 63   <- this value is generated 127 rolls *after*
       block 2, roll 62      the prior one which Math.random() outputted
       block 2, roll 61

    rolls: list of constraints for consecutive Math.random() float outputs
    Each roll can be:
        float               [known value between 0.0 and 1.0]
        (float, float)      [known range of (low, high) values]
        or None             [no constraint for this output]

    Returns list of all possible RNG solutions or [] if no solution found
    """
    solutions = []
    for offset in range(min(len(rolls), BLOCK_SIZE)):
        knowns = []
        if offset:
            block = rolls[0:offset][::-1]
            # If we have some initial offset, then the first block
            # needs to have the rest of the block filled out with nulls
            block.extend(None for _ in range(BLOCK_SIZE - len(block)))
            knowns.extend(block)

        for i in range(offset, len(rolls), BLOCK_SIZE):
            block = rolls[i : i + BLOCK_SIZE]
            # For every subsequent block, we need to fill the
            # start of the block with nulls instead of the end
            block.extend(None for _ in range(BLOCK_SIZE - len(block)))
            block = block[::-1]
            knowns.extend(block)

        states = solve_in_rng_order(knowns)
        if not states:
            continue

        for state in states:
            for i in range((offset or BLOCK_SIZE) - 1):
                state = xs128p(*state)

            solutions.append(
                {
                    "state": state,
                    "offset": (offset or BLOCK_SIZE) - 1,
                    "roll": state_to_double(state[0]),
                    "crossesBlockBoundary": len(knowns) > BLOCK_SIZE,
                }
            )

    return solutions
