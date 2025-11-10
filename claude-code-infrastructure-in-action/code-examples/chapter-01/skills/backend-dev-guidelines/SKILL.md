# 後端開發指南

本技能提供 TypeScript 後端開發的最佳實踐、設計模式和程式碼範例。

## 適用場景

- 實作 RESTful API 控制器
- 設計服務層架構
- 實作資料存取層
- 錯誤處理與驗證
- 測試策略

---

## 1. 控制器設計原則

### 1.1 單一職責

每個控制器方法應該只處理一個業務操作。

**✅ 好的做法**：

```typescript
class UserController {
  constructor(private userService: UserService) {}

  /**
   * 創建新使用者
   */
  async createUser(req: Request, res: Response): Promise<void> {
    const userData = req.body;
    const user = await this.userService.create(userData);
    res.status(201).json({ data: user });
  }

  /**
   * 更新使用者資料
   */
  async updateUser(req: Request, res: Response): Promise<void> {
    const { id } = req.params;
    const userData = req.body;
    const user = await this.userService.update(id, userData);
    res.json({ data: user });
  }
}
```

**❌ 避免**：

```typescript
class UserController {
  // 不要在一個方法中處理多種操作
  async handleUser(req: Request, res: Response): Promise<void> {
    const action = req.query.action;

    if (action === 'create') {
      // 創建邏輯
    } else if (action === 'update') {
      // 更新邏輯
    } else if (action === 'delete') {
      // 刪除邏輯
    }
  }
}
```

### 1.2 標準化錯誤處理

使用統一的錯誤處理中介層，拋出語義化錯誤。

```typescript
// errors/AppError.ts
export class AppError extends Error {
  constructor(
    public message: string,
    public statusCode: number,
    public isOperational: boolean = true
  ) {
    super(message);
    Object.setPrototypeOf(this, AppError.prototype);
  }
}

export class BadRequestError extends AppError {
  constructor(message: string) {
    super(message, 400);
  }
}

export class NotFoundError extends AppError {
  constructor(message: string) {
    super(message, 404);
  }
}

// controllers/UserController.ts
class UserController {
  async createUser(req: Request, res: Response): Promise<void> {
    try {
      const user = await this.userService.create(req.body);
      res.status(201).json({ data: user });
    } catch (error) {
      // 拋出語義化錯誤，由全域處理器捕獲
      throw new BadRequestError('無法創建使用者');
    }
  }

  async getUser(req: Request, res: Response): Promise<void> {
    const user = await this.userService.findById(req.params.id);

    if (!user) {
      throw new NotFoundError('使用者不存在');
    }

    res.json({ data: user });
  }
}
```

### 1.3 驗證與授權

**基本原則**：
- 控制器層：基本格式驗證、身份驗證
- 服務層：業務邏輯驗證

```typescript
import { body, param, validationResult } from 'express-validator';

class UserController {
  // 驗證規則定義
  static createUserValidation = [
    body('email').isEmail().withMessage('無效的郵箱格式'),
    body('password')
      .isLength({ min: 8 })
      .withMessage('密碼至少 8 個字元'),
    body('name').notEmpty().withMessage('姓名不能為空')
  ];

  // 控制器方法
  async createUser(req: Request, res: Response): Promise<void> {
    // 檢查驗證結果
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      throw new BadRequestError('驗證失敗');
    }

    // 業務邏輯驗證在 service 中進行
    const user = await this.userService.create(req.body);
    res.status(201).json({ data: user });
  }
}

// 路由配置
router.post(
  '/users',
  authenticate,  // 身份驗證中介層
  UserController.createUserValidation,  // 格式驗證
  (req, res) => userController.createUser(req, res)
);
```

---

## 2. 服務層設計

服務層負責業務邏輯，不應該包含 HTTP 相關的程式碼。

### 2.1 服務層結構

```typescript
// services/UserService.ts
export class UserService {
  constructor(
    private userRepository: UserRepository,
    private emailService: EmailService
  ) {}

  /**
   * 創建使用者
   * - 業務邏輯驗證
   * - 資料處理
   * - 發送通知
   */
  async create(userData: CreateUserDTO): Promise<User> {
    // 業務邏輯驗證
    const existingUser = await this.userRepository.findByEmail(userData.email);
    if (existingUser) {
      throw new BadRequestError('郵箱已被使用');
    }

    // 資料處理
    const hashedPassword = await bcrypt.hash(userData.password, 10);
    const user = await this.userRepository.create({
      ...userData,
      password: hashedPassword
    });

    // 發送通知
    await this.emailService.sendWelcomeEmail(user.email);

    return user;
  }

  /**
   * 查詢使用者
   */
  async findById(id: string): Promise<User | null> {
    return this.userRepository.findById(id);
  }

  /**
   * 更新使用者
   */
  async update(id: string, userData: UpdateUserDTO): Promise<User> {
    const user = await this.userRepository.findById(id);
    if (!user) {
      throw new NotFoundError('使用者不存在');
    }

    return this.userRepository.update(id, userData);
  }
}
```

### 2.2 依賴注入

使用依賴注入使服務層易於測試。

```typescript
// 使用 TypeDI 或其他 DI 容器
import { Service, Inject } from 'typedi';

@Service()
export class UserService {
  constructor(
    @Inject('UserRepository') private userRepository: UserRepository,
    @Inject('EmailService') private emailService: EmailService
  ) {}

  // 方法實作...
}
```

---

## 3. 資料存取層（Repository 模式）

Repository 模式隔離資料庫邏輯，使其易於測試和更換。

### 3.1 Repository 介面

```typescript
// repositories/interfaces/IUserRepository.ts
export interface IUserRepository {
  findById(id: string): Promise<User | null>;
  findByEmail(email: string): Promise<User | null>;
  create(userData: CreateUserDTO): Promise<User>;
  update(id: string, userData: UpdateUserDTO): Promise<User>;
  delete(id: string): Promise<void>;
  findAll(options: FindOptions): Promise<User[]>;
}
```

### 3.2 Repository 實作

```typescript
// repositories/UserRepository.ts
import { Repository } from 'typeorm';

export class UserRepository implements IUserRepository {
  constructor(private ormRepository: Repository<User>) {}

  async findById(id: string): Promise<User | null> {
    return this.ormRepository.findOne({ where: { id } });
  }

  async findByEmail(email: string): Promise<User | null> {
    return this.ormRepository.findOne({ where: { email } });
  }

  async create(userData: CreateUserDTO): Promise<User> {
    const user = this.ormRepository.create(userData);
    return this.ormRepository.save(user);
  }

  async update(id: string, userData: UpdateUserDTO): Promise<User> {
    await this.ormRepository.update(id, userData);
    const updatedUser = await this.findById(id);

    if (!updatedUser) {
      throw new NotFoundError('使用者不存在');
    }

    return updatedUser;
  }

  async delete(id: string): Promise<void> {
    await this.ormRepository.delete(id);
  }

  async findAll(options: FindOptions): Promise<User[]> {
    return this.ormRepository.find(options);
  }
}
```

---

## 4. 路由組織

### 4.1 模組化路由

```typescript
// routes/user.routes.ts
import { Router } from 'express';
import { UserController } from '../controllers/UserController';
import { authenticate } from '../middleware/auth';

const router = Router();
const userController = new UserController();

// 公開路由
router.post('/register', (req, res) => userController.register(req, res));
router.post('/login', (req, res) => userController.login(req, res));

// 受保護路由
router.use(authenticate);  // 所有後續路由都需要認證

router.get('/profile', (req, res) => userController.getProfile(req, res));
router.put('/profile', (req, res) => userController.updateProfile(req, res));
router.delete('/account', (req, res) => userController.deleteAccount(req, res));

export default router;
```

### 4.2 版本控制

```typescript
// routes/index.ts
import { Router } from 'express';
import userRoutesV1 from './v1/user.routes';
import userRoutesV2 from './v2/user.routes';

const router = Router();

// API 版本路由
router.use('/v1/users', userRoutesV1);
router.use('/v2/users', userRoutesV2);

export default router;
```

---

## 5. 測試策略

### 5.1 單元測試（服務層）

```typescript
// __tests__/services/UserService.test.ts
import { UserService } from '../../services/UserService';
import { UserRepository } from '../../repositories/UserRepository';
import { EmailService } from '../../services/EmailService';

describe('UserService', () => {
  let userService: UserService;
  let mockUserRepository: jest.Mocked<UserRepository>;
  let mockEmailService: jest.Mocked<EmailService>;

  beforeEach(() => {
    // 創建 mock
    mockUserRepository = {
      findByEmail: jest.fn(),
      create: jest.fn(),
      findById: jest.fn()
    } as any;

    mockEmailService = {
      sendWelcomeEmail: jest.fn()
    } as any;

    userService = new UserService(mockUserRepository, mockEmailService);
  });

  describe('create', () => {
    it('應該成功創建使用者', async () => {
      const userData = {
        email: 'test@example.com',
        password: 'password123',
        name: 'Test User'
      };

      mockUserRepository.findByEmail.mockResolvedValue(null);
      mockUserRepository.create.mockResolvedValue({ id: '1', ...userData });

      const result = await userService.create(userData);

      expect(result).toBeDefined();
      expect(mockEmailService.sendWelcomeEmail).toHaveBeenCalledWith(userData.email);
    });

    it('應該拋出錯誤當郵箱已存在', async () => {
      mockUserRepository.findByEmail.mockResolvedValue({ id: '1' } as any);

      await expect(
        userService.create({ email: 'test@example.com', password: '123', name: 'Test' })
      ).rejects.toThrow('郵箱已被使用');
    });
  });
});
```

### 5.2 整合測試（控制器 + 服務）

```typescript
// __tests__/integration/user.test.ts
import request from 'supertest';
import app from '../../app';

describe('User API', () => {
  describe('POST /api/v1/users', () => {
    it('應該創建新使用者', async () => {
      const response = await request(app)
        .post('/api/v1/users')
        .send({
          email: 'test@example.com',
          password: 'password123',
          name: 'Test User'
        })
        .expect(201);

      expect(response.body.data).toHaveProperty('id');
      expect(response.body.data.email).toBe('test@example.com');
    });

    it('應該返回 400 當驗證失敗', async () => {
      const response = await request(app)
        .post('/api/v1/users')
        .send({
          email: 'invalid-email',
          password: '123'  // 太短
        })
        .expect(400);

      expect(response.body).toHaveProperty('errors');
    });
  });
});
```

---

## 總結

遵循這些原則將幫助你建構：

✅ **可維護**：清晰的分層架構
✅ **可測試**：依賴注入和介面
✅ **可擴展**：模組化設計
✅ **穩健**：完善的錯誤處理
✅ **安全**：多層驗證和授權

---

## 延伸閱讀

如需更詳細的主題說明，請參考：

- `resources/controller-patterns.md` - 控制器設計模式
- `resources/service-layer.md` - 服務層架構
- `resources/data-access-layer.md` - 資料存取層
- `resources/error-handling.md` - 錯誤處理策略
- `resources/testing.md` - 測試最佳實踐
- `resources/api-versioning.md` - API 版本控制
- `resources/authentication.md` - 身份驗證與授權
