# 任務：測試覆蓋率提升

## 情境

專案的測試覆蓋率需要提升。目前覆蓋率為 [X]%，目標是達到 [Y]%。

覆蓋率報告位置：
[coverage/lcov-report/index.html 或其他位置]

優先處理的模組：
[列出覆蓋率最低或最重要的模組]

## 目標

1. 將整體測試覆蓋率從 [X]% 提升至 [Y]%
2. 為低覆蓋率的檔案新增有意義的測試
3. 確保新增的測試都能通過
4. 測試要涵蓋邊界條件和錯誤處理

## 約束

- 只新增測試，不修改原始碼（除非發現 bug）
- 測試要有意義，不是為了覆蓋率而覆蓋
- 遵循專案現有的測試風格
- 每個測試檔案對應一個原始碼檔案

## 完成條件

當以下所有條件都滿足時，此任務視為完成：

1. [ ] 覆蓋率達到目標：`npm run coverage` 顯示 >= [Y]%
2. [ ] 所有測試通過：`npm test` 返回 exit code 0
3. [ ] 沒有 skipped 或 pending 的測試

## 工作流程

1. **分析覆蓋率報告**
   ```bash
   npm run coverage
   # 查看哪些檔案覆蓋率最低
   ```

2. **識別低覆蓋檔案**
   - 列出覆蓋率低於平均的檔案
   - 優先處理核心業務邏輯

3. **逐檔案新增測試**
   對於每個低覆蓋檔案：
   a. 閱讀原始碼，理解功能
   b. 識別未被測試的分支/函數
   c. 撰寫測試案例
   d. 執行測試確認通過
   e. 重新生成覆蓋率報告

4. **驗證整體覆蓋率**
   ```bash
   npm run coverage
   # 確認達到目標
   ```

## 測試撰寫指南

### 好的測試

```typescript
describe('calculateTotal', () => {
  it('should return sum of all items', () => {
    const items = [{ price: 10 }, { price: 20 }];
    expect(calculateTotal(items)).toBe(30);
  });

  it('should return 0 for empty array', () => {
    expect(calculateTotal([])).toBe(0);
  });

  it('should handle negative prices', () => {
    const items = [{ price: -10 }, { price: 20 }];
    expect(calculateTotal(items)).toBe(10);
  });
});
```

### 要避免的測試

```typescript
// ❌ 沒有意義的測試
it('should exist', () => {
  expect(calculateTotal).toBeDefined();
});

// ❌ 測試實作細節
it('should call internal method', () => {
  // 不應該測試私有方法
});
```

## 注意事項

- 優先測試公開的 API，而非內部實作
- 邊界條件（空陣列、null、極大/極小值）要涵蓋
- 錯誤處理路徑也需要測試
- 避免過度 mock，可能導致測試與實際行為脫節
