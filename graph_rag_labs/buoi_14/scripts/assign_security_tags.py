import os
import sys
import json
import pandas as pd

# Add buoi_14 directory to sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
buoi14_dir = os.path.dirname(script_dir)
if buoi14_dir not in sys.path:
    sys.path.insert(0, buoi14_dir)

from src.config import ROLES

def classify_security_level(row: pd.Series) -> list[str]:
    """
    Classify a chunk into allowed roles based on title, document_id, and text keywords.
    
    Security Levels & Roles:
    1. HR Confidential: ["Admin", "HR"]
       - Human resources, salaries, rewards, recruitment, appointment, insurance regulations.
    2. Credit & Risk Management: ["Admin", "Risk_Manager", "Staff"]
       - Credit, risk, capital adequacy ratios, foreign exchange reserves, indirect investment limits.
    3. General Public / Operational: ["Admin", "HR", "Risk_Manager", "Staff", "Guest"]
       - General regulations, licensing, cooperative laws, public procedures.
    """
    text_lower = str(row.get('text', '')).lower()
    title_lower = str(row.get('title', '')).lower()
    combined_content = f"{title_lower} {text_lower}"

    # Keywords for HR Confidential
    hr_keywords = [
        'bảo hiểm', 'nhân sự', 'lương', 'thưởng', 'tuyển dụng', 
        'bổ nhiệm', 'lao động', 'tập sự', 'kỷ luật', 'người lao động'
    ]
    
    # Keywords for Risk & Credit Management
    risk_keywords = [
        'tín dụng', 'rủi ro', 'hạn mức', 'phê duyệt', 'cho vay', 
        'tài sản bảo đảm', 'tỷ lệ an toàn vốn', 'ngoại hối', 
        'quản lý dự trữ', 'đầu tư gián tiếp', 'thẩm định'
    ]

    if any(k in combined_content for k in hr_keywords):
        return ["Admin", "HR"]
    elif any(k in combined_content for k in risk_keywords):
        return ["Admin", "Risk_Manager", "Staff"]
    else:
        return ["Admin", "HR", "Risk_Manager", "Staff", "Guest"]


def main():
    input_file = os.path.join(buoi14_dir, "data", "processed", "chunks_normalized.csv")
    output_file = os.path.join(buoi14_dir, "data", "processed", "chunks_secure.csv")
    
    print(f"Reading input dataset from: {input_file}")
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file not found at {input_file}")

    df = pd.read_csv(input_file)
    print(f"Loaded {len(df)} chunks from input file.")

    # Assign allowed_roles column
    df['roles_list'] = df.apply(classify_security_level, axis=1)
    df['allowed_roles'] = df['roles_list'].apply(lambda roles: json.dumps(roles, ensure_ascii=False))
    
    # Drop temporary column before saving
    df_output = df.drop(columns=['roles_list'])

    # Ensure target output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    df_output.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"Successfully saved tagged dataset to: {output_file}\n")

    # ==============================================================================
    # VERIFICATION & AUDIT
    # ==============================================================================
    print("=" * 70)
    print("VERIFICATION AND STATISTICAL SUMMARY")
    print("=" * 70)
    
    # 1. Null / Empty Check
    invalid_rows = df_output[df_output['allowed_roles'].isna() | (df_output['allowed_roles'] == '[]')]
    if len(invalid_rows) == 0:
        print("✔ Check Passed: Every chunk has at least 1 role assigned (0 null/empty rows).")
    else:
        print(f"✖ Check Failed: Found {len(invalid_rows)} invalid rows!")

    # 2. Statistics by security group
    print("\n--- Statistics by Security Group ---")
    counts = df_output['allowed_roles'].value_counts()
    for role_pattern, count in counts.items():
        percentage = (count / len(df_output)) * 100
        print(f"• Pattern: {role_pattern:<50} | Count: {count:>3} ({percentage:.1f}%)")

    # 3. Individual Role Coverage
    print("\n--- Individual Role Access Coverage ---")
    role_coverage = {role: 0 for role in ROLES}
    for roles_json in df_output['allowed_roles']:
        roles = json.loads(roles_json)
        for role in roles:
            if role in role_coverage:
                role_coverage[role] += 1

    for role, count in role_coverage.items():
        percentage = (count / len(df_output)) * 100
        print(f"• Role [{role:<12}]: Can access {count:>3}/{len(df_output)} chunks ({percentage:.1f}%)")

    # 4. Representative Sample Output (3 security levels)
    print("\n" + "=" * 70)
    print("REPRESENTATIVE SAMPLES FOR 3 SECURITY LEVELS")
    print("=" * 70)

    patterns = [
        ('["Admin", "HR"]', 'Mức 1: Bảo mật Nhân sự (HR Restricted)'),
        ('["Admin", "Risk_Manager", "Staff"]', 'Mức 2: Quản trị Rủi ro & Tín dụng (Risk/Credit Restricted)'),
        ('["Admin", "HR", "Risk_Manager", "Staff", "Guest"]', 'Mức 3: Tài liệu Nội quy / Công khai (General/Guest Accessible)')
    ]

    for pattern, description in patterns:
        sample = df_output[df_output['allowed_roles'] == pattern].iloc[0]
        print(f"\n📌 {description}:")
        print(f"   • Chunk ID       : {sample['chunk_id']}")
        print(f"   • Document ID    : {sample['document_id']}")
        print(f"   • Document Title : {sample['title']}")
        print(f"   • Allowed Roles  : {sample['allowed_roles']}")
        print(f"   • Text Snippet   : {str(sample['text'])[:120].strip()}...")

    print("\n" + "=" * 70)
    print("Security tagging completed successfully.")

if __name__ == "__main__":
    main()
