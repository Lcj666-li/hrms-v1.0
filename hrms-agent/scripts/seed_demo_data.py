"""造演示数据：30 个员工 + 3 个月考勤 + 请假 + 薪资（幂等）。

    python scripts/seed_demo_data.py

只写 HRMS 业务库（hrms），不动 HRMS 代码；用户名 emp01~emp30，密码与现有 employee 一致。
"""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta

import pymysql

DB = dict(host="127.0.0.1", port=3306, user="root", password="123456", database="hrms", charset="utf8mb4")
EMPLOYEE_COUNT = 30
random.seed(20261106)


def conn():
    return pymysql.connect(**DB, autocommit=True)


def main() -> int:
    with conn() as c, c.cursor() as cur:
        cur.execute("SELECT id FROM role WHERE code='employee'")
        role_id = cur.fetchone()[0]
        cur.execute("SELECT id FROM department ORDER BY id LIMIT 1")
        dept_id = cur.fetchone()[0]
        cur.execute("SELECT id FROM position ORDER BY id LIMIT 1")
        pos_id = cur.fetchone()[0]
        cur.execute("SELECT password_hash FROM user WHERE username='employee'")
        pwd = cur.fetchone()[0]
        cur.execute("SELECT id, leave_type_id FROM leave_request ORDER BY id LIMIT 1")
        existing_leave = cur.fetchall()

        names = ["张伟", "王芳", "李强", "刘洋", "陈静", "杨帆", "赵敏", "黄磊", "周婷", "吴昊",
                 "徐丽", "孙鹏", "马超", "朱琳", "胡军", "郭敏", "林峰", "何静", "高翔", "罗娟",
                 "郑浩", "梁爽", "谢婷", "宋涛", "唐宁", "许强", "韩雪", "冯磊", "邓丽", "曹阳"]
        created = 0
        for i in range(EMPLOYEE_COUNT):
            username = f"emp{i + 1:02d}"
            cur.execute("SELECT id FROM user WHERE username=%s", (username,))
            if cur.fetchone():
                continue
            cur.execute(
                "INSERT INTO user (username, password_hash, role_id, name, gender, phone, email,"
                " department_id, position_id, hire_date, is_active) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1)",
                (username, pwd, role_id, names[i % len(names)],
                 random.choice(["男", "女"]), f"1380000{i:04d}", f"{username}@example.com",
                 dept_id, pos_id, date(2024, 1, 1) + timedelta(days=random.randint(0, 600))),
            )
            created += 1

        cur.execute("SELECT id FROM user WHERE role_id=%s", (role_id,))
        emp_ids = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT id FROM leave_type WHERE is_active=1")
        type_ids = [r[0] for r in cur.fetchall()]

        # 考勤：最近 90 天的工作日
        cur.execute("SELECT COUNT(*) FROM attendance")
        before_att = cur.fetchone()[0]
        today = date.today()
        att_rows = 0
        for emp in emp_ids:
            for d in range(90):
                day = today - timedelta(days=d)
                if day.weekday() >= 5:
                    continue
                r = random.random()
                if r < 0.03:
                    status, ci, co = "absent", None, None
                elif r < 0.10:
                    status, ci, co = "late", "09:35:00", "18:10:00"
                else:
                    status, ci, co = "normal", "08:55:00", "18:05:00"
                cur.execute(
                    "INSERT IGNORE INTO attendance (user_id, `date`, check_in, check_out, status) VALUES (%s,%s,%s,%s,%s)",
                    (emp, day, ci, co, status))
                att_rows += 1

        # 请假：20 条
        cur.execute("SELECT COUNT(*) FROM leave_request")
        before_leave = cur.fetchone()[0]
        for _ in range(20 if before_leave < 25 else 0):
            emp = random.choice(emp_ids)
            start = today - timedelta(days=random.randint(1, 60))
            end = start + timedelta(days=random.randint(0, 2))
            cur.execute(
                "INSERT INTO leave_request (user_id, leave_type_id, start_date, end_date, reason, status)"
                " VALUES (%s,%s,%s,%s,%s,%s)",
                (emp, random.choice(type_ids), start, end, "演示数据",
                 random.choice(["approved", "approved", "pending", "rejected"])))

        # 薪资：最近 3 个月
        cur.execute("SELECT COUNT(*) FROM salary_record")
        before_sal = cur.fetchone()[0]
        cur.execute("SELECT id FROM user WHERE username='manager'")
        manager_id = cur.fetchone()[0]
        for emp in emp_ids:
            base = random.choice([8000, 9500, 11000, 12500, 15000])
            for m in range(3):
                month = (today.replace(day=1) - timedelta(days=30 * m)).strftime("%Y-%m")
                deduction = random.choice([0, 0, 100, 200, 350])
                actual = base - deduction - 0
                cur.execute(
                    "INSERT IGNORE INTO salary_record (user_id, salary_month, base_salary, attendance_deduction,"
                    " leave_deduction, bonus, social_security, tax, actual_salary, status, created_by, issued_at)"
                    " VALUES (%s,%s,%s,%s,0,%s,%s,%s,%s,'issued',%s,NOW())",
                    (emp, month, base, deduction, random.choice([0, 500, 1000]),
                     round(base * 0.105, 2), round(base * 0.03, 2), actual, manager_id))

        cur.execute("SELECT COUNT(*) FROM attendance")
        after_att = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM leave_request")
        after_leave = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM salary_record")
        after_sal = cur.fetchone()[0]

    print(f"新增员工 {created} 个（emp01~emp{EMPLOYEE_COUNT:02d}，密码同 employee）")
    print(f"考勤 {before_att} -> {after_att}（+{after_att - before_att}）")
    print(f"请假 {before_leave} -> {after_leave}（+{after_leave - before_leave}）")
    print(f"薪资 {before_sal} -> {after_sal}（+{after_sal - before_sal}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
