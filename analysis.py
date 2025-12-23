"""
Comparison of SWIFT and mBridge cross-border payment flows for a 1,000,000 RMB transfer.
Generates summary metrics and a lightweight SVG visualization (no external deps).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class Step:
    name: str
    fee_rate: float  # expressed as decimal fraction (e.g., 0.001 for 0.1%)
    time_minutes: float


@dataclass
class FlowResult:
    total_fee: float
    total_time_minutes: float
    fx_loss: float
    final_amount: float


class PaymentFlow:
    def __init__(self, steps: List[Step], fx_loss_rate: float = 0.0):
        self.steps = steps
        self.fx_loss_rate = fx_loss_rate

    def run(self, principal: float) -> FlowResult:
        total_fee = sum(principal * step.fee_rate for step in self.steps)
        total_time_minutes = sum(step.time_minutes for step in self.steps)
        fx_loss = principal * self.fx_loss_rate
        final_amount = principal - total_fee - fx_loss
        return FlowResult(
            total_fee=total_fee,
            total_time_minutes=total_time_minutes,
            fx_loss=fx_loss,
            final_amount=final_amount,
        )


def format_currency(amount: float) -> str:
    return f"{amount:,.0f}"


principal = 1_000_000  # RMB

swift_steps = [
    Step("中国银行X", 0.001, 60),
    Step("代理行Y", 0.0015, 12 * 60),
    Step("泰国银行Z", 0.002, 6 * 60),
    Step("泰国企业B入账", 0.0005, 60),
]

mbridge_steps = [
    Step("数字人民币系统", 0.0005, 5),
    Step("mBridge平台兑换", 0.001, 10),
    Step("泰国央行系统", 0.0005, 5),
    Step("泰国企业B入账", 0.0, 5),
]

swift_flow = PaymentFlow(swift_steps, fx_loss_rate=0.003)
mbridge_flow = PaymentFlow(mbridge_steps, fx_loss_rate=0.0)

swift_result = swift_flow.run(principal)
mbridge_result = mbridge_flow.run(principal)

cost_saving = swift_result.total_fee + swift_result.fx_loss - (
    mbridge_result.total_fee + mbridge_result.fx_loss
)
time_saving_minutes = swift_result.total_time_minutes - mbridge_result.total_time_minutes
fx_saving = swift_result.fx_loss - mbridge_result.fx_loss

print("SWIFT模式:")
print(f"  总手续费: {format_currency(swift_result.total_fee)} RMB")
print(f"  汇率损失: {format_currency(swift_result.fx_loss)} RMB")
print(f"  总成本: {format_currency(swift_result.total_fee + swift_result.fx_loss)} RMB")
print(
    f"  总耗时: {swift_result.total_time_minutes / 60:.1f} 小时"
)
print(
    f"  最终到账金额（按人民币等值）: {format_currency(swift_result.final_amount)} RMB\n"
)

print("mBridge模式:")
print(f"  总手续费: {format_currency(mbridge_result.total_fee)} RMB")
print(f"  汇率损失: {format_currency(mbridge_result.fx_loss)} RMB")
print(f"  总成本: {format_currency(mbridge_result.total_fee + mbridge_result.fx_loss)} RMB")
print(
    f"  总耗时: {mbridge_result.total_time_minutes:.0f} 分钟"
)
print(
    f"  最终到账金额（按人民币等值）: {format_currency(mbridge_result.final_amount)} RMB\n"
)

print("差异：")
print(f"  成本节省: {format_currency(cost_saving)} RMB")
print(
    f"  时间节省: {time_saving_minutes / 60:.1f} 小时"
)
print(f"  汇率损失节省: {format_currency(fx_saving)} RMB")


# Simple SVG visualization (no external dependencies)
def render_svg():
    width, height = 700, 350
    margin = 70

    def bar(x, y, w, h, color, label=""):
        return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{color}" /><text x="{x + w/2}" y="{y - 5}" text-anchor="middle" font-size="12">{label}</text>'

    # Cost bars (stacked: fee + fx)
    max_cost = max(swift_result.total_fee + swift_result.fx_loss, mbridge_result.total_fee)
    cost_scale = (height / 2 - margin) / max_cost if max_cost else 1

    swift_fee_h = swift_result.total_fee * cost_scale
    swift_fx_h = swift_result.fx_loss * cost_scale
    mbridge_fee_h = mbridge_result.total_fee * cost_scale
    mbridge_fx_h = mbridge_result.fx_loss * cost_scale

    cost_group = []
    bar_width = 80
    spacing = 140
    base_y = height / 2 + 100
    base_x = margin

    # SWIFT cost bar
    swift_x = base_x
    swift_fee_y = base_y - swift_fee_h
    swift_fx_y = swift_fee_y - swift_fx_h
    cost_group.append(bar(swift_x, swift_fee_y, bar_width, swift_fee_h, "#1f77b4", f"费 {format_currency(swift_result.total_fee)}"))
    cost_group.append(bar(swift_x, swift_fx_y, bar_width, swift_fx_h, "#ff7f0e", f"汇 {format_currency(swift_result.fx_loss)}"))
    cost_group.append(f'<text x="{swift_x + bar_width/2}" y="{base_y + 15}" text-anchor="middle" font-size="14">SWIFT</text>')

    # mBridge cost bar
    mbridge_x = base_x + spacing
    mbridge_fee_y = base_y - mbridge_fee_h
    mbridge_fx_y = mbridge_fee_y - mbridge_fx_h
    cost_group.append(bar(mbridge_x, mbridge_fee_y, bar_width, mbridge_fee_h, "#1f77b4", f"费 {format_currency(mbridge_result.total_fee)}"))
    if mbridge_fx_h:
        cost_group.append(bar(mbridge_x, mbridge_fx_y, bar_width, mbridge_fx_h, "#ff7f0e", f"汇 {format_currency(mbridge_result.fx_loss)}"))
    cost_group.append(f'<text x="{mbridge_x + bar_width/2}" y="{base_y + 15}" text-anchor="middle" font-size="14">mBridge</text>')

    cost_group.append(f'<text x="{margin}" y="{margin - 20}" font-size="16">成本对比（RMB）</text>')

    # Time bars
    time_max = max(swift_result.total_time_minutes / 60, mbridge_result.total_time_minutes / 60)
    time_scale = (height / 2 - margin) / time_max if time_max else 1

    time_group = []
    time_base_y = height - margin
    time_base_x = base_x + 2 * spacing

    swift_time_h = (swift_result.total_time_minutes / 60) * time_scale
    mbridge_time_h = (mbridge_result.total_time_minutes / 60) * time_scale

    time_group.append(bar(time_base_x, time_base_y - swift_time_h, bar_width, swift_time_h, "#2ca02c", f"{swift_result.total_time_minutes/60:.1f}h"))
    time_group.append(f'<text x="{time_base_x + bar_width/2}" y="{time_base_y + 15}" text-anchor="middle" font-size="14">SWIFT</text>')

    time_group.append(bar(time_base_x + spacing, time_base_y - mbridge_time_h, bar_width, mbridge_time_h, "#d62728", f"{mbridge_result.total_time_minutes/60:.2f}h"))
    time_group.append(f'<text x="{time_base_x + spacing + bar_width/2}" y="{time_base_y + 15}" text-anchor="middle" font-size="14">mBridge</text>')
    time_group.append(f'<text x="{time_base_x}" y="{margin - 20}" font-size="16">时间对比（小时）</text>')

    svg_content = f"""
    <svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}'>
        <rect width='100%' height='100%' fill='white' />
        <g>{''.join(cost_group)}</g>
        <g>{''.join(time_group)}</g>
    </svg>
    """.strip()

    with open("outputs/comparison.svg", "w", encoding="utf-8") as f:
        f.write(svg_content)


render_svg()
print("图表已保存至 outputs/comparison.svg")
