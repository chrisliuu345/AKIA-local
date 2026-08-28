with open('analysis/doe/definitive_screening.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Change 1: Line 120 - O(n) inverse permutation
old1 = '    df["RunOrder"] = [int(np.where(perm == i)[0][0]) + 1 for i in range(n_runs)]'
new1 = '    inv_perm = np.empty(n_runs, dtype=int)\n    inv_perm[perm] = np.arange(n_runs) + 1\n    df["RunOrder"] = inv_perm'

assert old1 in content, 'Change 1 target not found'
content = content.replace(old1, new1, 1)

# Change 2: Line 169 - Remove .copy()
old2 = 'data = df[[response_col] + factor_cols].dropna().copy()'
new2 = 'data = df[[response_col] + factor_cols].dropna()'

assert old2 in content, 'Change 2 target not found'
content = content.replace(old2, new2, 1)

with open('analysis/doe/definitive_screening.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Changes 1 and 2 applied successfully')
