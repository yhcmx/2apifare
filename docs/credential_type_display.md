# 凭证类型显示功能说明

## 功能概述

为了让用户清楚地区分 **Gemini CLI 凭证** 和 **Antigravity 凭证**，系统新增了凭证类型识别和显示功能。

## 修改内容

### 1. 后端 API 修改

**文件**: `src/web_routes.py`

**修改内容**:
- 在 `/creds/status` API 返回的每个凭证信息中，新增 `credential_type` 字段
- 类型判断逻辑：
  - 如果文件名包含 `accounts.toml` → `"ant"` (Antigravity)
  - 其他 `.json` 文件 → `"cli"` (Gemini CLI)

```python
# 判断凭证类型：accounts.toml 是 ANT 凭证，其他 JSON 文件是 CLI 凭证
credential_type = "ant" if "accounts.toml" in filename.lower() else "cli"

result = {
    "status": file_status,
    "content": credential_data,
    "filename": os.path.basename(filename),
    "backend_type": backend_type,
    "user_email": file_status.get("user_email"),
    "credential_type": credential_type,  # 新增字段
}
```

### 2. 前端统计区域修改

**文件**: `front/control_panel.html`

#### 2.1 HTML 结构修改

**原来的统计区域**（单一统计）:
```html
<div class="stats-container">
    <div class="stat-item total">
        <span class="stat-number">0</span>
        <span class="stat-label">总计</span>
    </div>
    <div class="stat-item normal">
        <span class="stat-number">0</span>
        <span class="stat-label">正常</span>
    </div>
    <div class="stat-item disabled">
        <span class="stat-number">0</span>
        <span class="stat-label">禁用</span>
    </div>
</div>
```

**新的统计区域**（分类统计）:
```html
<div class="stats-container">
    <!-- CLI 凭证统计 -->
    <div style="display: flex; gap: 10px; background: #e3f2fd; border-radius: 8px; flex: 1;">
        <div style="font-weight: bold; color: #1976d2; min-width: 100px; text-align: center; border-right: 2px solid #1976d2;">
            Gemini CLI
        </div>
        <div class="stat-item total">
            <span class="stat-number" id="statCliTotal">0</span>
            <span class="stat-label">总计</span>
        </div>
        <div class="stat-item normal">
            <span class="stat-number" id="statCliNormal">0</span>
            <span class="stat-label">正常</span>
        </div>
        <div class="stat-item disabled">
            <span class="stat-number" id="statCliDisabled">0</span>
            <span class="stat-label">禁用</span>
        </div>
    </div>

    <!-- ANT 凭证统计 -->
    <div style="display: flex; gap: 10px; background: #f3e5f5; border-radius: 8px; flex: 1;">
        <div style="font-weight: bold; color: #7b1fa2; min-width: 100px; text-align: center; border-right: 2px solid #7b1fa2;">
            Antigravity
        </div>
        <div class="stat-item total">
            <span class="stat-number" id="statAntTotal">0</span>
            <span class="stat-label">总计</span>
        </div>
        <div class="stat-item normal">
            <span class="stat-number" id="statAntNormal">0</span>
            <span class="stat-label">正常</span>
        </div>
        <div class="stat-item disabled">
            <span class="stat-number" id="statAntDisabled">0</span>
            <span class="stat-label">禁用</span>
        </div>
    </div>
</div>
```

#### 2.2 JavaScript 统计逻辑修改

**`calculateStats()` 函数**:

**修改前**（单一统计）:
```javascript
function calculateStats() {
    statsData = {
        total: 0,
        normal: 0,
        disabled: 0
    };

    for (const [fullPath, credInfo] of Object.entries(credsData)) {
        statsData.total++;
        if (credInfo.status.disabled) {
            statsData.disabled++;
        } else {
            statsData.normal++;
        }
    }
}
```

**修改后**（分类统计）:
```javascript
function calculateStats() {
    statsData = {
        // CLI 凭证统计
        cli: {
            total: 0,
            normal: 0,
            disabled: 0
        },
        // ANT 凭证统计
        ant: {
            total: 0,
            normal: 0,
            disabled: 0
        },
        // 总计
        total: 0,
        normal: 0,
        disabled: 0
    };

    for (const [fullPath, credInfo] of Object.entries(credsData)) {
        // 获取凭证类型（默认为 cli）
        const credType = credInfo.credential_type || 'cli';

        // 总计统计
        statsData.total++;
        statsData[credType].total++;

        if (credInfo.status.disabled) {
            statsData.disabled++;
            statsData[credType].disabled++;
        } else {
            statsData.normal++;
            statsData[credType].normal++;
        }
    }
}
```

**`updateStatsDisplay()` 函数**:

**修改前**:
```javascript
function updateStatsDisplay() {
    document.getElementById('statTotal').textContent = statsData.total;
    document.getElementById('statNormal').textContent = statsData.normal;
    document.getElementById('statDisabled').textContent = statsData.disabled;
}
```

**修改后**:
```javascript
function updateStatsDisplay() {
    // 更新 CLI 凭证统计
    document.getElementById('statCliTotal').textContent = statsData.cli.total;
    document.getElementById('statCliNormal').textContent = statsData.cli.normal;
    document.getElementById('statCliDisabled').textContent = statsData.cli.disabled;

    // 更新 ANT 凭证统计
    document.getElementById('statAntTotal').textContent = statsData.ant.total;
    document.getElementById('statAntNormal').textContent = statsData.ant.normal;
    document.getElementById('statAntDisabled').textContent = statsData.ant.disabled;
}
```

### 3. 凭证卡片类型标识

**修改位置**: `createCredCard()` 函数

**新增内容**:
```javascript
// 构建凭证类型标识
const credType = credInfo.credential_type || 'cli';
const credTypeDisplay = credType === 'cli' ? 'Gemini CLI' : 'Antigravity';
const credTypeBadgeColor = credType === 'cli' ? '#1976d2' : '#7b1fa2';
const credTypeBadgeBg = credType === 'cli' ? '#e3f2fd' : '#f3e5f5';
const credTypeBadge = `<span style="background: ${credTypeBadgeBg}; color: ${credTypeBadgeColor}; padding: 2px 8px; border-radius: 3px; font-size: 11px; font-weight: bold; margin-left: 8px; white-space: nowrap;">${credTypeDisplay}</span>`;
```

**显示效果**:
```
innate-agency-477614-e2-1763805851.json  [Gemini CLI]  已启用
accounts.toml                            [Antigravity]  已启用
```

## 视觉设计

### 配色方案

| 凭证类型 | 颜色主题 | 背景色 | 文字色 |
|---------|---------|--------|--------|
| **Gemini CLI** | 蓝色系 | #e3f2fd | #1976d2 |
| **Antigravity** | 紫色系 | #f3e5f5 | #7b1fa2 |

### 显示位置

1. **统计区域**: 页面顶部，并排显示两个统计卡片
2. **凭证卡片**: 文件名右侧，显示类型标签

## 使用效果

### 统计区域显示

```
┌──────────────────────────────────────────┐  ┌──────────────────────────────────────────┐
│   Gemini CLI  │  50  │  45  │   5       │  │  Antigravity │   3  │   2  │   1        │
│               │ 总计 │ 正常 │ 禁用      │  │              │ 总计 │ 正常 │ 禁用       │
└──────────────────────────────────────────┘  └──────────────────────────────────────────┘
```

### 凭证列表显示

```
☑ innate-agency-477614.json  [Gemini CLI]     yuzhib236@gmail.com      ✅已启用 无错误
☑ accounts.toml              [Antigravity]    developer@gmail.com      ✅已启用 无错误
☑ ec-burin23333.json         [Gemini CLI]     burin23333@gmail.com     ✅已启用 错误码: 429
```

## 技术细节

### 凭证类型判断逻辑

```python
# 在后端 web_routes.py 中
credential_type = "ant" if "accounts.toml" in filename.lower() else "cli"
```

**判断依据**:
- `accounts.toml` 文件 → Antigravity 凭证
- 其他 `.json` 文件 → Gemini CLI 凭证

### 数据结构

**返回的凭证信息**:
```json
{
    "creds": {
        "D:\\...\\creds\\innate-agency-477614.json": {
            "status": { "disabled": false, "error_codes": [] },
            "content": { ... },
            "filename": "innate-agency-477614.json",
            "backend_type": "file",
            "user_email": "yuzhib236@gmail.com",
            "credential_type": "cli"  // 新增字段
        },
        "D:\\...\\creds\\accounts.toml": {
            "status": { "disabled": false, "error_codes": [] },
            "content": { ... },
            "filename": "accounts.toml",
            "backend_type": "file",
            "user_email": "developer@gmail.com",
            "credential_type": "ant"  // 新增字段
        }
    }
}
```

## 优势和用户体验提升

### ✅ 清晰的分类统计
- 用户一眼就能看出有多少个 CLI 凭证和多少个 ANT 凭证
- 分别显示每种凭证的正常/禁用数量
- 便于管理和监控不同类型的凭证

### ✅ 明确的类型标识
- 每个凭证文件都有明显的类型标签
- 不会混淆不同来源的凭证
- 便于快速识别和操作

### ✅ 色彩区分
- 蓝色代表 Gemini CLI（官方主色）
- 紫色代表 Antigravity（区别于 CLI）
- 视觉上更容易区分

### ✅ 响应式设计
- 统计卡片并排显示，充分利用空间
- 类型标签使用 `white-space: nowrap` 防止换行
- 支持不同屏幕尺寸

## 兼容性说明

### 向后兼容
- 如果后端返回的凭证没有 `credential_type` 字段，默认识别为 `cli`
- 不影响现有功能的正常使用

### 数据迁移
- 无需迁移现有数据
- 新的类型识别逻辑基于文件名，自动识别

## 未来扩展

如果将来需要支持更多凭证类型，只需：
1. 在后端添加新的类型判断逻辑
2. 在前端添加新的统计区域和配色
3. 在 `statsData` 中添加新的类型统计对象

例如支持 Claude 凭证：
```javascript
statsData = {
    cli: { total: 0, normal: 0, disabled: 0 },
    ant: { total: 0, normal: 0, disabled: 0 },
    claude: { total: 0, normal: 0, disabled: 0 },  // 新增
    total: 0,
    normal: 0,
    disabled: 0
};
```

## 总结

通过这次改进，用户现在可以：
- 📊 **清晰查看** 不同类型凭证的统计数据
- 🏷️ **快速识别** 每个凭证文件的来源
- 🎨 **直观区分** 通过颜色快速辨别凭证类型
- 📈 **更好管理** 大量不同类型的凭证

这个功能大大提升了用户体验，让多凭证管理变得更加清晰和高效！
