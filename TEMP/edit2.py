with open('analysis/doe/definitive_screening.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Build the old block (lines 178-234 area)
old3 = """    # \u2500\u2500 \u4e3b\u6548\u5e94\u8ba1\u7b97 \u2500\u2500
    grand_mean = float(np.mean(response))
    effects = {}
    for i, f in enumerate(factor_cols):
        mask_high = design[:, i] > 0
        mask_low = design[:, i] < 0
        n_high = np.sum(mask_high)
        n_low = np.sum(mask_low)
        if n_high > 0 and n_low > 0:
            effect = float(np.mean(response[mask_high]) - np.mean(response[mask_low]))
        else:
            effect = 0.0
        effects[f] = round(effect, 6)

    # \u2500\u2500 ANOVA \u2500\u2500
    ss_total = float(np.sum((response - grand_mean) ** 2))
    df_total = n - 1

    ss_model = 0.0
    ss_effects = {}
    df_model = 0

    for f in factor_cols:
        idx = factor_cols.index(f)
        mask_high = design[:, idx] > 0
        mask_low = design[:, idx] < 0
        n_high = np.sum(mask_high)
        n_low = np.sum(mask_low)
        if n_high > 0 and n_low > 0:
            effect = effects[f]
            ss_f = n * (effect / 2) ** 2
        else:
            ss_f = 0.0
        ss_effects[f] = round(ss_f, 6)
        ss_model += ss_f
        df_model += 1

    ss_error = max(ss_total - ss_model, 0.0)
    df_error = max(df_total - df_model, 1)

    f_values = {}
    p_values = {}
    ms_effects = {}
    for f in factor_cols:
        ms_f = ss_effects[f]
        ms_effects[f] = round(ms_f, 6)
        if df_error > 0 and ss_error > 0:
            f_val = ms_f / (ss_error / df_error)
            p_val = 1.0 - stats.f.cdf(max(f_val, 0), 1, df_error)
        elif ss_error == 0 and df_error > 0:
            # \u5b8c\u7f8e\u62df\u5408: F \u503c\u65e0\u7a77\u5927\uff0cp \u503c\u8d8b\u8fd1 0
            f_val = float('inf')
            p_val = 0.0
        else:
            f_val = 0.0
            p_val = 1.0
        f_values[f] = round(f_val, 4) if f_val != float('inf') else f_val
        p_values[f] = round(p_val, 6)"""

new3 = """    # \u2500\u2500 \u4e3b\u6548\u5e94\u8ba1\u7b97\uff08\u5411\u91cf\u5316\uff09\u2500\u2500
    grand_mean = float(np.mean(response))
    high_mask = design > 0
    low_mask = design < 0
    n_high = high_mask.sum(axis=0)
    n_low = low_mask.sum(axis=0)
    sum_high = (response[:, np.newaxis] * high_mask).sum(axis=0)
    sum_low = (response[:, np.newaxis] * low_mask).sum(axis=0)
    valid = (n_high > 0) & (n_low > 0)
    effects_arr = np.where(valid, sum_high / n_high - sum_low / n_low, 0.0)

    effects = {f: round(float(effects_arr[i]), 6) for i, f in enumerate(factor_cols)}

    # \u2500\u2500 ANOVA\uff08\u5411\u91cf\u5316\uff09\u2500\u2500
    ss_total = float(np.sum((response - grand_mean) ** 2))
    df_total = n - 1

    ss_arr = np.where(valid, n * (effects_arr / 2) ** 2, 0.0)
    ss_effects = {f: round(float(ss_arr[i]), 6) for i, f in enumerate(factor_cols)}
    ss_model = float(ss_arr.sum())
    df_model = int(valid.sum())

    ss_error = max(ss_total - ss_model, 0.0)
    df_error = max(df_total - df_model, 1)

    # F \u503c\u548c p \u503c\uff08\u5411\u91cf\u5316\uff09
    ms_arr = ss_arr.copy()
    if df_error > 0 and ss_error > 0:
        mse = ss_error / df_error
        f_arr = ms_arr / mse
        p_arr = 1.0 - stats.f.cdf(np.maximum(f_arr, 0.0), 1, df_error)
    elif ss_error == 0 and df_error > 0:
        f_arr = np.full(k, float('inf'))
        p_arr = np.zeros(k)
    else:
        f_arr = np.zeros(k)
        p_arr = np.ones(k)

    f_values = {}
    p_values = {}
    ms_effects = {}
    for i, f in enumerate(factor_cols):
        ms_effects[f] = round(float(ms_arr[i]), 6)
        f_values[f] = round(float(f_arr[i]), 4) if not np.isinf(f_arr[i]) else float('inf')
        p_values[f] = round(float(p_arr[i]), 6)"""

assert old3 in content, 'Change 3 target not found'
content = content.replace(old3, new3, 1)

with open('analysis/doe/definitive_screening.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Change 3 applied successfully')
