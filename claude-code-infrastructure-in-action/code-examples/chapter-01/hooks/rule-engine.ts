import * as fs from 'fs';
import * as path from 'path';
import minimatch from 'minimatch';

/**
 * 技能規則配置介面
 */
interface SkillRule {
  type: 'domain' | 'guardrail' | 'tooling';
  enforcement: 'suggest' | 'warn' | 'block';
  priority: 'critical' | 'high' | 'medium' | 'low';
  pathPatterns?: string[];
  promptTriggers?: {
    keywords?: string[];
    intents?: string[];
  };
  exclusions?: {
    paths?: string[];
  };
}

/**
 * 規則配置檔案格式
 */
interface RuleConfig {
  version: string;
  skills: Record<string, SkillRule>;
}

/**
 * 規則引擎 - 負責匹配檔案路徑和提示內容到相應的技能
 */
export class RuleEngine {
  private config: RuleConfig;
  private projectRoot: string;
  private configCache: { mtime: number; config: RuleConfig } | null = null;

  constructor(projectRoot: string) {
    this.projectRoot = projectRoot;
    this.config = this.loadConfig();
  }

  /**
   * 載入規則配置（帶快取）
   */
  private loadConfig(): RuleConfig {
    const configPath = path.join(
      this.projectRoot,
      '.claude/skills/skill-rules.json'
    );

    if (!fs.existsSync(configPath)) {
      console.warn(`規則配置不存在: ${configPath}`);
      return { version: '1.0', skills: {} };
    }

    try {
      const stat = fs.statSync(configPath);

      // 檢查快取是否有效
      if (this.configCache && this.configCache.mtime === stat.mtimeMs) {
        return this.configCache.config;
      }

      // 讀取並解析配置
      const content = fs.readFileSync(configPath, 'utf-8');
      const config = JSON.parse(content) as RuleConfig;

      // 更新快取
      this.configCache = { mtime: stat.mtimeMs, config };

      return config;
    } catch (error) {
      console.error(`載入規則配置失敗: ${error}`);
      return { version: '1.0', skills: {} };
    }
  }

  /**
   * 根據檔案路徑匹配技能
   * @param filePath 檔案路徑（相對於專案根目錄）
   * @returns 匹配的技能名稱清單（已排序）
   */
  matchByPath(filePath: string): string[] {
    const matchedSkills: string[] = [];

    for (const [skillName, rule] of Object.entries(this.config.skills)) {
      // 檢查排除規則
      if (this.isExcluded(filePath, rule)) {
        continue;
      }

      // 檢查路徑模式
      if (rule.pathPatterns) {
        for (const pattern of rule.pathPatterns) {
          if (minimatch(filePath, pattern, { matchBase: true })) {
            matchedSkills.push(skillName);
            break;
          }
        }
      }
    }

    return this.sortByPriority(matchedSkills);
  }

  /**
   * 根據提示內容匹配技能
   * @param prompt 使用者輸入的提示
   * @returns 匹配的技能名稱清單（已排序）
   */
  matchByPrompt(prompt: string): string[] {
    const matchedSkills: string[] = [];
    const lowerPrompt = prompt.toLowerCase();

    for (const [skillName, rule] of Object.entries(this.config.skills)) {
      if (!rule.promptTriggers) continue;

      let matched = false;

      // 關鍵字匹配
      if (rule.promptTriggers.keywords) {
        for (const keyword of rule.promptTriggers.keywords) {
          if (lowerPrompt.includes(keyword.toLowerCase())) {
            matched = true;
            break;
          }
        }
      }

      // 意圖模式匹配（正則表達式）
      if (!matched && rule.promptTriggers.intents) {
        for (const intentPattern of rule.promptTriggers.intents) {
          try {
            const regex = new RegExp(intentPattern, 'i');
            if (regex.test(prompt)) {
              matched = true;
              break;
            }
          } catch (error) {
            console.error(`無效的正則表達式: ${intentPattern}`, error);
          }
        }
      }

      if (matched) {
        matchedSkills.push(skillName);
      }
    }

    return this.sortByPriority(matchedSkills);
  }

  /**
   * 檢查檔案是否被排除
   */
  private isExcluded(filePath: string, rule: SkillRule): boolean {
    if (!rule.exclusions?.paths) return false;

    for (const pattern of rule.exclusions.paths) {
      if (minimatch(filePath, pattern, { matchBase: true })) {
        return true;
      }
    }

    return false;
  }

  /**
   * 按優先級排序技能
   */
  private sortByPriority(skills: string[]): string[] {
    const priorityMap: Record<string, number> = {
      critical: 4,
      high: 3,
      medium: 2,
      low: 1
    };

    return skills.sort((a, b) => {
      const ruleA = this.config.skills[a];
      const ruleB = this.config.skills[b];

      if (!ruleA || !ruleB) return 0;

      const priorityA = priorityMap[ruleA.priority] || 0;
      const priorityB = priorityMap[ruleB.priority] || 0;

      return priorityB - priorityA;
    });
  }

  /**
   * 取得技能的詳細資訊
   */
  getSkillInfo(skillName: string): SkillRule | undefined {
    return this.config.skills[skillName];
  }

  /**
   * 重新載入配置（清除快取）
   */
  reload(): void {
    this.configCache = null;
    this.config = this.loadConfig();
  }
}
