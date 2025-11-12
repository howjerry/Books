import { RuleEngine } from './rule-engine';
import * as path from 'path';

/**
 * 檢查檔案路徑並匹配相應的技能
 *
 * 用法: node -r ts-node/register check-skills.ts <file-path>
 */

// 從命令列參數取得檔案路徑
const filePath = process.argv[2];

if (!filePath) {
  console.error('用法: check-skills.ts <file-path>');
  process.exit(1);
}

// 取得專案根目錄
const projectRoot = process.env.CLAUDE_PROJECT_DIR || process.cwd();

// 初始化規則引擎
const engine = new RuleEngine(projectRoot);

// 匹配技能
const matchedSkills = engine.matchByPath(filePath);

// 輸出結果
if (matchedSkills.length === 0) {
  // 沒有匹配的技能，靜默退出
  process.exit(0);
}

console.log('\n建議激活以下技能：');
matchedSkills.forEach((skill, index) => {
  const info = engine.getSkillInfo(skill);
  console.log(`${index + 1}. ${skill} (優先級: ${info?.priority}, 強制程度: ${info?.enforcement})`);
});

console.log(''); // 空行，增加可讀性
