import { RuleEngine } from './rule-engine';
import * as fs from 'fs';
import * as path from 'path';

/**
 * 分析使用者提示並建議相關技能
 *
 * 此腳本從 stdin 讀取 JSON 格式的資料，包含：
 * - prompt: 使用者輸入的提示
 * - workingDirectory: 當前工作目錄
 * - recentFiles: 最近編輯的檔案清單
 */

try {
  // 從 stdin 讀取輸入
  const input = fs.readFileSync(0, 'utf-8');
  const data = JSON.parse(input);

  // 提取資料
  const userPrompt: string = data.prompt || '';
  const workingDir: string = data.workingDirectory || process.cwd();
  const recentFiles: string[] = data.recentFiles || [];

  // 如果沒有提示內容，直接退出
  if (!userPrompt.trim()) {
    process.exit(0);
  }

  // 初始化規則引擎
  const projectRoot = process.env.CLAUDE_PROJECT_DIR || workingDir;
  const engine = new RuleEngine(projectRoot);

  // 根據提示匹配技能
  const skillsByPrompt = engine.matchByPrompt(userPrompt);

  // 根據最近編輯的檔案匹配技能
  const skillsByFiles = recentFiles
    .flatMap(filePath => engine.matchByPath(filePath))
    .filter((skill, index, self) => self.indexOf(skill) === index); // 去重

  // 合併並去重所有匹配的技能
  const allSkills = [...new Set([...skillsByPrompt, ...skillsByFiles])];

  // 如果沒有匹配的技能，靜默退出
  if (allSkills.length === 0) {
    process.exit(0);
  }

  // 輸出建議
  console.log('\n💡 根據你的提示和當前上下文，建議激活以下技能：\n');

  allSkills.forEach((skill, index) => {
    const info = engine.getSkillInfo(skill);
    console.log(`${index + 1}. **${skill}** (${info?.enforcement})`);

    // 嘗試顯示技能簡介（從 SKILL.md 提取第一個標題）
    const skillPath = path.join(projectRoot, '.claude', 'skills', skill, 'SKILL.md');
    if (fs.existsSync(skillPath)) {
      try {
        const content = fs.readFileSync(skillPath, 'utf-8');
        const lines = content.split('\n');
        const firstHeading = lines.find(line => line.trim().startsWith('#'));

        if (firstHeading) {
          const description = firstHeading.replace(/^#+\s*/, '').trim();
          console.log(`   ${description}`);
        }
      } catch (error) {
        // 忽略讀取錯誤
      }
    }

    console.log(''); // 空行分隔
  });

  console.log('這些技能將幫助 Claude 提供更精準的指導。\n');

  process.exit(0);
} catch (error) {
  console.error('處理提示時發生錯誤:', error);
  process.exit(1);
}
