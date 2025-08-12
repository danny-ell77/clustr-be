---
inclusion: always
---

# 🚫 ZERO BLOAT POLICY - STRICTLY ENFORCED

## For AI Agents & Developers: Minimal Implementation ONLY

### ⚠️ **CRITICAL MANDATE:**
**Write the simplest code that works. No exceptions. No "future-proofing". No over-engineering.**

### ❌ **ABSOLUTELY FORBIDDEN:**

#### 🚫 **Over-Engineering Patterns**
```python
# DON'T: Unnecessary abstractions
class AbstractFactoryBuilderManager:
    def create_strategy_pattern_handler(self):
        return ComplexPatternFactory().build_with_strategy()

# DON'T: Complex inheritance hierarchies  
class BasePaymentProcessorAbstractManager(ABC):
    @abstractmethod
    def process_with_strategy_pattern(self):
        pass

# DON'T: Interfaces for simple functions
class PaymentProcessorInterface(Protocol):
    def process(self) -> PaymentResult: ...
```

#### 🚫 **Bloated Functions**
```python
# DON'T: Kitchen sink functions with too many responsibilities
def process_payment_and_send_notifications_and_update_analytics_and_log_everything(
    transaction, user, cluster, settings, config, metadata, options, flags
):
    # 200 lines of mixed responsibilities
```

#### 🚫 **Speculative Code**
```python
# DON'T: "Maybe we'll need this later" code
def future_feature_placeholder():
    """TODO: Implement advanced AI recommendations"""
    pass

# DON'T: Unused parameters "just in case"
def simple_function(required_param, unused_future_param=None, another_unused=None):
    return process(required_param)
```

### ✅ **MANDATED APPROACH:**

#### 🎯 **Minimal, Focused Functions**
```python
# DO: Simple, single-purpose functions
def send_notification(event_name, recipients, cluster, context):
    """Send notification to recipients."""
    try:
        from core.common.includes import notifications
        return notifications.send(event_name, recipients, cluster, context)
    except Exception as e:
        logger.error(f"Notification failed: {e}")
        return False

# DO: Direct, obvious implementation
def get_user_bills(user, cluster):
    """Get bills for a user."""
    return Bill.objects.filter(user_id=user.id, cluster=cluster)
```

#### 🎯 **Lean Implementation Rules**
1. **Max 50 lines** per function
2. **Max 5 parameters** per function  
3. **Single responsibility** - one function, one purpose
4. **No unused code** - delete immediately
5. **No "TODO" placeholders** - implement or don't commit

### 📏 **MEASUREMENT CRITERIA:**

| Metric | Limit | Enforcement |
|--------|-------|-------------|
| Function lines | 50 max | STRICT |
| Function parameters | 5 max | STRICT |  
| File size | 500 lines max | STRICT |
| Cyclomatic complexity | 10 max | STRICT |
| Import statements | Only what's used | STRICT |

### 🔍 **MANDATORY PRE-COMMIT CHECKLIST:**

- [ ] **Can this be simpler?** (If yes, simplify it)
- [ ] **Does every line serve a purpose?** (If no, delete it)
- [ ] **Are all imports used?** (If no, remove them)
- [ ] **Are all parameters used?** (If no, remove them)
- [ ] **Is this the minimal code that works?** (If no, reduce it)
- [ ] **Would a 12-year-old understand this code?** (If no, simplify it)

### 🚨 **AI Agent Instructions:**

1. **REJECT** any request for abstract base classes unless absolutely proven necessary
2. **DELETE** unused imports, parameters, and code immediately  
3. **SIMPLIFY** complex logic into smaller, focused functions
4. **QUESTION** every line: "Is this necessary RIGHT NOW?"
5. **PREFER** Django/Python stdlib over external packages
6. **WRITE** functions that do ONE thing well
7. **REFUSE** to implement speculative features

### ⚡ **Performance Priorities:**

1. **Readable** > Clever
2. **Simple** > Complex  
3. **Direct** > Abstract
4. **Obvious** > Elegant
5. **Working** > Perfect

### 🎯 **Implementation Examples:**

```python
# ✅ PERFECT: Minimal, clear, focused
def create_bill(cluster, user, title, amount, due_date):
    """Create a bill."""
    bill = Bill.objects.create(
        cluster=cluster,
        user_id=user.id,
        title=title,
        amount=amount,
        due_date=due_date
    )
    logger.info(f"Bill created: {bill.id}")
    return bill

# ✅ PERFECT: Simple error handling  
def get_wallet_balance(wallet):
    """Get wallet balance."""
    try:
        return wallet.balance
    except AttributeError:
        return Decimal('0.00')

# ✅ PERFECT: Direct database query
def get_overdue_bills(cluster):
    """Get overdue bills for cluster."""
    return Bill.objects.filter(
        cluster=cluster,
        due_date__lt=timezone.now(),
        paid_at__isnull=True
    )
```

### 🧠 **Mental Model:**
**Every line of code is a liability. Write less. Accomplish more. Delete ruthlessly.**

**If you can't explain it in one sentence, it's too complex.**
