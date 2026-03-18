from flask import Flask, render_template, request, redirect, flash
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "your_secret_key"

FILE_PATH = "expenses.txt"

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        amount_str = (request.form.get("amount") or "").strip()
        category = (request.form.get("category") or "").strip()
        note = (request.form.get("note") or "").strip()

        try:
            amount = int(amount_str)
        except ValueError:
            flash("金額を入力してね")
            return redirect("/")
        
        if amount <= 0:
            flash("金額は1円以上にしてね")
            return redirect("/")
        
        if category == "":
            flash("カテゴリを選んでね")
            return redirect("/")

        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        line = f"{now},{amount},{category},{note}\n"

        with open(FILE_PATH, "a", encoding="utf-8") as f:
            f.write(line)

        return redirect(f"/?month={datetime.now().strftime('%Y-%m')}")
    
# 支出の読み込み
    expenses = []
    try:
        with open(FILE_PATH, "r", encoding="utf-8") as f:
            for line in f:
                raw = line.strip()
                date, amount, category, note = raw.split(",", 3)

                expenses.append({
                    "date": date,
                    "amount": int(amount),
                    "category": category,
                    "note": note,
                    "raw": raw
                })
    except FileNotFoundError:
        pass

# ここからが（月切り替え）の本体
    now_dt = datetime.now()
    current_month = now_dt.strftime("%Y-%m")

# URLからmonthを受け取る(例 /?month=2026-02)
    selected_month =(request.args.get("month") or current_month)
    keyword = request.args.get("keyword", "")

    selected_year = selected_month[:4]

    year_expenses = [e for e in expenses if e["date"][:4] == selected_year]

    monthly_breakdown = {str(i).zfill(2): 0 for i in range(1, 13)}

    for e in year_expenses:
        month = e["date"][5:7]
        monthly_breakdown[month] += e["amount"]

    month_totals = {}
    for e in year_expenses:
        m = e["date"][5:7]
        month_totals[m] = month_totals.get(m, 0) + e["amount"]

    month_ranking = sorted(
        [(m, amt) for m, amt in month_totals.items() if amt > 0],
        key=lambda x: x[1],
        reverse=True
    )

    year_total = sum(e["amount"] for e in year_expenses)

    last_year = str(int(selected_year) - 1)
    last_year_expenses = [e for e in expenses if e["date"][:4] == last_year]
    last_year_total = sum(e["amount"] for e in last_year_expenses)
    year_diff = year_total - last_year_total

    # プルダウン候補（月一覧）を作る
    months = sorted({e["date"][:7] for e in expenses}, reverse=True)
    if current_month not in months:
        months = [current_month] + months

    # selected_monthが候補にない変な値なら今月に戻す
    if selected_month not in months:
        selected_month = current_month

    selected_year = selected_month[:4]
    selected_month_only = selected_month[5:]

    last_year = str(int(selected_year) - 1)
    last_same_month = f"{last_year}-{selected_month_only}"

    # 前月
    first_day = datetime.strptime(selected_month + "-01", "%Y-%m-%d")
    prev_month = (first_day - timedelta(days=1)).strftime("%Y-%m")

    # 月で絞り込み
    filtered_expenses = [e for e in expenses if e["date"][:7] == selected_month]

    # 検索キーワードで絞り込み
    if keyword:
        filtered_expenses = [
            e for e in filtered_expenses
            if keyword.lower() in e["note"].lower()
        ]

    filtered_expenses.reverse()

    # 合計（表示中の月）
    total = sum(e["amount"] for e in filtered_expenses)

    # 去年同月の支出だけ集める
    last_same_month_expenses = [
        e for e in expenses if e["date"][:7] == last_same_month
    ]

    # 去年同月の合計
    last_same_month_total = sum(e["amount"] for e in last_same_month_expenses)

    # 差（今月 ― 去年同月）
    month_diff = total - last_same_month_total

    if last_same_month_total > 0:
        yoy_percent = round((total - last_same_month_total) / last_same_month_total * 100, 1)
    else:
        yoy_percent = None

    # 前月合計
    prev_total = sum(e["amount"] for e in expenses if e["date"][:7] == prev_month)

    monthly_totals = {
        "current": total,
        "last": prev_total
    }

    # カテゴリ別（表示中の）月だけ
    category_totals = {
        "食費": 0,
        "交通": 0,
        "娯楽": 0,
        "その他": 0
    }

    for e in filtered_expenses:
        if e["category"] in category_totals:
            category_totals[e["category"]] += e["amount"]

    if total > 0:
        category_ranking = sorted(
            [(cat, amt, round(amt / total * 100, 1)) for cat, amt in category_totals.items() if amt > 0],
            key=lambda x: x[1],
            reverse=True
        )

    else:
        category_ranking = []

    return render_template("index.html", expenses=filtered_expenses, total=total, category_totals=category_totals, monthly_totals=monthly_totals, months=months, selected_month=selected_month, prev_month=prev_month,category_ranking=category_ranking,year_total=year_total,selected_year=selected_year, monthly_breakdown=monthly_breakdown, month_ranking=month_ranking, last_year=last_year, last_year_total=last_year_total, year_diff=year_diff, last_same_month=last_same_month, last_same_month_total=last_same_month_total, month_diff=month_diff, yoy_percent=yoy_percent)

@app.route("/delete/", methods=["POST"])
def delete():
    raw = request.form.get("raw", "")
    month = request.form.get("month", "")

    try:
        with open(FILE_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return redirect("/" + (f"?month={month}" if month else ""))
    
    target = raw + "\n"
    
    for i, line in enumerate(lines):
        if line.rstrip("\n") == raw:
            del lines[i]
            break

    with open(FILE_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)

    return redirect("/" + (f"?month={month}" if month else ""))

@app.route("/edit", methods=["POST"])
def edit():
    raw = request.form.get("raw", "")
    month = request.form.get("month", "")

    # rawを分解して初期値にする
    date, amount, category, note = raw.split(",", 3)
    return render_template("edit.html", raw=raw, date=date, amount=amount, category=category, note=note, salected_month=month)

@app.route("/update", methods=["POST"])
def update():
    old_raw =request.form.get("old_raw", "")
    month = request.form.get("month", "")

    date = request.form.get("date", "")
    amount = request.form.get("amount", "").strip()
    category = request.form.get("category", "")
    note = request.form.get("note", "")

    new_raw = f"{date},{amount},{category},{note}"

    try:
        with open(FILE_PATH, "r", encoding="utf-8")as f:
            lines = f.readlines()
    except FileNotFoundError:
        return redirect(f"/?month={month}" if month else "/")
    
    for i, line in enumerate(lines):
        if line.rstrip("\n") == old_raw:
            lines[i] = new_raw + "\n"
            break

    with open(FILE_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)

    return redirect(f"/?month={month}" if month else "/")

if __name__ == "__main__":
    app.run(debug=True)