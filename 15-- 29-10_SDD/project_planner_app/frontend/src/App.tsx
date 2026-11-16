import { useCallback, useEffect, useMemo, useState } from 'react'
import type { FormEvent, DragEvent, CSSProperties, ReactNode } from 'react'
import {
  Activity, ArrowLeft, ArrowRight, CalendarDays, Check, CheckCircle2,
  CircleHelp, Clock3, Flag, LayoutGrid, ListChecks, LogOut, Plus, Sparkles,
  TrendingUp, X, Zap, Pencil,
} from 'lucide-react'
import { api, getToken, setToken } from './api'
import type { Analytics, Category, Goal, Task, User } from './types'

type View = 'day' | 'week' | 'month' | 'progress'
type AuthResponse = { access_token: string; user: User }
type NoteResponse = { body: string }

const pad = (n: number) => String(n).padStart(2, '0')
const iso = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
const fromISO = (s: string) => { const [y, m, d] = s.split('-').map(Number); return new Date(y, m - 1, d) }
const addDays = (d: Date, n: number) => { const x = new Date(d); x.setDate(x.getDate() + n); return x }
const startOfWeek = (d: Date) => addDays(d, -((d.getDay() + 6) % 7))
const startOfMonth = (d: Date) => new Date(d.getFullYear(), d.getMonth(), 1)
const endOfMonth = (d: Date) => new Date(d.getFullYear(), d.getMonth() + 1, 0)
const monthName = (d: Date) => d.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })
const dayLabel = (d: Date) => d.toLocaleDateString(undefined, { weekday: 'short' })
const fullDate = (d: Date) => d.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })
const todayISO = iso(new Date())

function App() {
  const [user, setUser] = useState<User | null>(null)
  const [view, setView] = useState<View>('month')
  const [selectedDate, setSelectedDate] = useState(todayISO)
  const [categories, setCategories] = useState<Category[]>([])
  const [tasks, setTasks] = useState<Task[]>([])
  const [goals, setGoals] = useState<Goal[]>([])
  const [analytics, setAnalytics] = useState<Analytics | null>(null)
  const [note, setNote] = useState('')
  const [noteDraft, setNoteDraft] = useState('')
  const [quickOpen, setQuickOpen] = useState(false)
  const [categoryOpen, setCategoryOpen] = useState(false)
  const [goalOpen, setGoalOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [isRegister, setIsRegister] = useState(true)
  const [taskTitle, setTaskTitle] = useState('')
  const [taskDate, setTaskDate] = useState(todayISO)
  const [taskPriority, setTaskPriority] = useState<'high' | 'medium' | 'low'>('medium')
  const [taskCategory, setTaskCategory] = useState('')
  const [recurrence, setRecurrence] = useState('none')
  const [weekdays, setWeekdays] = useState<number[]>([])
  const [weeklyTarget, setWeeklyTarget] = useState(3)
  const [linkedGoal, setLinkedGoal] = useState('')
  const [categoryName, setCategoryName] = useState('')
  const [categoryColor, setCategoryColor] = useState('#3d9c8b')
  const [goalTitle, setGoalTitle] = useState('')
  const [goalLevel, setGoalLevel] = useState('weekly')
  const [goalStart, setGoalStart] = useState(todayISO)
  const [goalDue, setGoalDue] = useState(iso(addDays(new Date(), 6)))
  const [goalTaskIds, setGoalTaskIds] = useState<number[]>([])
  const [goalParent, setGoalParent] = useState('')
  const [moveTask, setMoveTask] = useState<Task | null>(null)
  const [editingTask, setEditingTask] = useState<Task | null>(null)
  const [editTitle, setEditTitle] = useState('')
  const [editPriority, setEditPriority] = useState<'high' | 'medium' | 'low'>('medium')
  const [editCategory, setEditCategory] = useState('')
  const [intervalDays, setIntervalDays] = useState(2)
  const [moveDate, setMoveDate] = useState(todayISO)

  const allGoals = useMemo(() => {
    const flattened: Goal[] = []
    const visit = (items: Goal[]) => items.forEach(goal => { flattened.push(goal); visit(goal.children || []) })
    visit(goals)
    return flattened
  }, [goals])

  const selected = useMemo(() => fromISO(selectedDate), [selectedDate])
  const weekStart = useMemo(() => startOfWeek(selected), [selected])
  const weekEnd = useMemo(() => addDays(weekStart, 6), [weekStart])
  const monthStart = useMemo(() => startOfMonth(selected), [selected])
  const monthEnd = useMemo(() => endOfMonth(selected), [selected])
  const period = useMemo(() => {
    if (view === 'day') return { type: 'day', key: selectedDate, start: selected, end: selected }
    if (view === 'week') return { type: 'week', key: iso(weekStart), start: weekStart, end: weekEnd }
    return { type: 'month', key: `${selected.getFullYear()}-${pad(selected.getMonth() + 1)}`, start: monthStart, end: monthEnd }
  }, [view, selectedDate, selected, weekStart, weekEnd, monthStart, monthEnd])

  const loadWorkspace = useCallback(async () => {
    setBusy(true)
    setError('')
    try {
      const rangeStart = addDays(startOfMonth(fromISO(selectedDate)), -35)
      const rangeEnd = addDays(endOfMonth(fromISO(selectedDate)), 45)
      const [cats, taskRows, goalRows, stats] = await Promise.all([
        api<Category[]>('/categories'),
        api<Task[]>(`/tasks?start_date=${iso(rangeStart)}&end_date=${iso(rangeEnd)}`),
        api<Goal[]>('/goals'),
        api<Analytics>(`/analytics?start_date=${iso(period.start)}&end_date=${iso(period.end)}`),
      ])
      setCategories(cats); setTasks(taskRows); setGoals(goalRows); setAnalytics(stats)
      const noteResult = await api<NoteResponse>(`/notes?period_type=${period.type}&period_key=${encodeURIComponent(period.key)}`)
      setNote(noteResult.body); setNoteDraft(noteResult.body)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load your workspace')
    } finally { setBusy(false) }
  }, [selectedDate, period])

  useEffect(() => {
    const token = getToken()
    if (!token) return
    api<User>('/auth/me').then(setUser).catch(() => setToken(null))
  }, [])

  useEffect(() => { if (user) loadWorkspace() }, [user, loadWorkspace])

  useEffect(() => {
    const openQuick = () => { setTaskDate(selectedDate); setQuickOpen(true) }
    window.addEventListener("open-quick-add", openQuick)
    return () => window.removeEventListener("open-quick-add", openQuick)
  }, [selectedDate])

  const changeDate = (delta: number) => {
    if (view === 'month') setSelectedDate(iso(new Date(selected.getFullYear(), selected.getMonth() + delta, 1)))
    else if (view === 'week') setSelectedDate(iso(addDays(selected, delta * 7)))
    else setSelectedDate(iso(addDays(selected, delta)))
  }

  const authenticate = async (event: FormEvent) => {
    event.preventDefault(); setError(''); setBusy(true)
    try {
      const payload = isRegister ? { email, full_name: fullName, password } : { email, password }
      const result = await api<AuthResponse>(isRegister ? '/auth/register' : '/auth/login', { method: 'POST', body: JSON.stringify(payload) })
      setToken(result.access_token); setUser(result.user); setNotice(isRegister ? 'Your workspace is ready.' : 'Welcome back.')
    } catch (e) { setError(e instanceof Error ? e.message : 'Authentication failed') }
    finally { setBusy(false) }
  }

  const refresh = async () => { if (user) await loadWorkspace() }

  const submitTask = async (event: FormEvent) => {
    event.preventDefault(); if (!taskTitle.trim()) return
    setBusy(true); setError('')
    try {
      const created = await api<Task>('/tasks', { method: 'POST', body: JSON.stringify({
        title: taskTitle.trim(), scheduled_date: taskDate, priority: taskPriority,
        category_id: taskCategory ? Number(taskCategory) : null,
        recurrence_type: recurrence, interval_days: recurrence === 'custom' ? intervalDays : 1, weekdays, weekly_target: recurrence === 'weekly_count' ? weeklyTarget : 0,
      }) })
      if (linkedGoal) await api(`/goals/${linkedGoal}/tasks`, { method: 'POST', body: JSON.stringify({ task_id: created.id }) })
      setTaskTitle(''); setRecurrence('none'); setWeekdays([]); setLinkedGoal(''); setQuickOpen(false)
      setNotice('Task added to your plan.'); await refresh()
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not add task') }
    finally { setBusy(false) }
  }

  const toggleTask = async (task: Task) => {
    if (task.scheduled_date < todayISO) return
    try { await api(`/tasks/${task.id}/status`, { method: 'PATCH', body: JSON.stringify({ completed: !task.completed }) }); await refresh() }
    catch (e) { setError(e instanceof Error ? e.message : 'Could not update task') }
  }

  const openEdit = (task: Task) => {
    setEditingTask(task); setEditTitle(task.title); setEditPriority(task.priority); setEditCategory(String(task.category_id))
  }

  const saveEdit = async (event: FormEvent) => {
    event.preventDefault(); if (!editingTask) return
    try {
      await api(`/tasks/${editingTask.id}`, { method: 'PATCH', body: JSON.stringify({ title: editTitle, priority: editPriority, category_id: Number(editCategory) }) })
      setEditingTask(null); setNotice('Task updated.'); await refresh()
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not update task') }
  }

  const move = async (task: Task, destination: string) => {
    try {
      await api(`/tasks/${task.id}/move`, { method: 'POST', body: JSON.stringify({ destination_date: destination }) })
      setMoveTask(null); setNotice(`Moved “${task.title}” to ${destination}.`); await refresh()
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not move task') }
  }

  const addCategory = async (event: FormEvent) => {
    event.preventDefault()
    try {
      await api('/categories', { method: 'POST', body: JSON.stringify({ name: categoryName, color: categoryColor }) })
      setCategoryName(''); setCategoryOpen(false); await refresh(); setNotice('Category created.')
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not create category') }
  }

  const addGoal = async (event: FormEvent) => {
    event.preventDefault()
    try {
      const created = await api<Goal>('/goals', { method: 'POST', body: JSON.stringify({
        title: goalTitle, level: goalLevel, start_date: goalStart, due_date: goalDue, tracking_mode: 'linked',
        parent_goal_id: goalParent ? Number(goalParent) : null,
      }) })
      for (const taskId of goalTaskIds) await api(`/goals/${created.id}/tasks`, { method: 'POST', body: JSON.stringify({ task_id: taskId }) })
      setGoalTitle(''); setGoalTaskIds([]); setGoalParent(''); setGoalOpen(false); await refresh(); setNotice('Goal created and linked.')
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not create goal') }
  }

  const saveNote = async () => {
    try {
      await api('/notes', { method: 'PUT', body: JSON.stringify({ period_type: period.type, period_key: period.key, body: noteDraft }) })
      setNote(noteDraft); setNotice('Notes saved.')
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not save notes') }
  }

  const beginDrag = (event: DragEvent, task: Task) => event.dataTransfer.setData('taskId', String(task.id))
  const dropOnDate = (event: DragEvent, dateKey: string) => {
    event.preventDefault(); const id = Number(event.dataTransfer.getData('taskId'))
    const task = tasks.find(x => x.id === id)
    if (task && dateKey >= todayISO) void move(task, dateKey)
  }

  const visibleOn = (day: Date) => tasks.filter(t => t.scheduled_date === iso(day) && t.status !== 'moved' && t.status !== 'cancelled')
  const overdue = tasks.filter(t => t.scheduled_date < todayISO && !t.completed && t.status === 'open')
  const titleForView = view === 'day' ? fullDate(selected) : view === 'week' ? `${weekStart.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })} – ${weekEnd.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}` : view === 'month' ? monthName(selected) : 'Your progress'

  if (!user) return <AuthScreen {...{ email, setEmail, password, setPassword, fullName, setFullName, isRegister, setIsRegister, authenticate, busy, error }} />

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><Sparkles size={19} /></div><div><strong>daymark</strong><span>make room for progress</span></div></div>
      <div className="nav-label">WORKSPACE</div>
      <nav className="main-nav">
        <NavButton active={view === 'day'} icon={<ListChecks size={17}/>} label="Today" onClick={() => setView('day')} />
        <NavButton active={view === 'week'} icon={<CalendarDays size={17}/>} label="Week" onClick={() => setView('week')} />
        <NavButton active={view === 'month'} icon={<LayoutGrid size={17}/>} label="Month" onClick={() => setView('month')} />
        <NavButton active={view === 'progress'} icon={<TrendingUp size={17}/>} label="Progress" onClick={() => setView('progress')} />
      </nav>
      <div className="sidebar-section-head"><span className="nav-label">CATEGORIES</span><button className="icon-button tiny" aria-label="Add category" onClick={() => setCategoryOpen(true)}><Plus size={15}/></button></div>
      <div className="category-list">
        {categories.map(c => <div className="category-item" key={c.id}><span className="category-dot" style={{ background: c.color }}/><span>{c.name}</span></div>)}
      </div>
      <div className="sidebar-bottom">
        <div className="user-chip"><div className="avatar">{(user.full_name || user.email).slice(0, 1).toUpperCase()}</div><div className="user-details"><strong>{user.full_name || 'Your workspace'}</strong><span>{user.email}</span></div><button className="icon-button tiny" title="Sign out" onClick={() => { setToken(null); setUser(null) }}><LogOut size={16}/></button></div>
      </div>
    </aside>

    <main className="main-panel">
      <header className="topbar">
        <div className="breadcrumb">Workspace <span>/</span> {view === 'progress' ? 'Progress' : view[0].toUpperCase() + view.slice(1)}</div>
        <div className="top-actions"><span className="today-pill"><span className="live-dot"/>{new Date().toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })}</span><button className="primary-button compact" onClick={() => { setTaskDate(selectedDate); setQuickOpen(true) }}><Plus size={16}/> Add task</button></div>
      </header>

      <div className="page-content">
        {error && <div className="toast error-toast"><CircleHelp size={16}/>{error}<button onClick={() => setError('')}><X size={15}/></button></div>}
        {notice && <div className="toast success-toast"><CheckCircle2 size={16}/>{notice}<button onClick={() => setNotice('')}><X size={15}/></button></div>}
        <div className="page-heading">
          <div><div className="eyebrow">{view === 'progress' ? 'A LITTLE BETTER, EVERY DAY' : 'YOUR PLANNING SPACE'}</div><h1>{titleForView}</h1><p>{view === 'progress' ? 'Small actions add up. Here is how your plans are moving.' : 'Make a plan that leaves room for real life.'}</p></div>
          {view !== 'progress' && <div className="date-controls"><button className="icon-button" aria-label="Previous period" onClick={() => changeDate(-1)}><ArrowLeft size={17}/></button><button className="today-button" onClick={() => setSelectedDate(todayISO)}>Today</button><button className="icon-button" aria-label="Next period" onClick={() => changeDate(1)}><ArrowRight size={17}/></button></div>}
        </div>

        {view === 'day' && <DailyView {...{ selected, visibleOn, categories, overdue, toggleTask, setMoveTask, openEdit }} />}
        {view === 'week' && <WeeklyView {...{ weekStart, visibleOn, selectedDate, setSelectedDate, dropOnDate, beginDrag, tasks, toggleTask, setMoveTask, openEdit }} />}
        {view === 'month' && <MonthlyView {...{ selected, monthStart, visibleOn, selectedDate, setSelectedDate, dropOnDate, beginDrag, tasks, analytics }} />}
        {view === 'progress' && <ProgressView analytics={analytics} goals={goals} />}

        {view !== 'progress' && <div className="bottom-grid">
          <section className="panel notes-panel"><div className="panel-heading"><div><span className="panel-kicker">REFLECTION</span><h2>{view === 'day' ? 'Daily notes' : view === 'week' ? 'Notes for this week' : 'Notes for this month'}</h2></div><span className="soft-icon"><Activity size={17}/></span></div><textarea value={noteDraft} onChange={e => setNoteDraft(e.target.value)} onBlur={() => { if (noteDraft !== note) void saveNote() }} placeholder="Capture thoughts, ideas, or something you want to remember…"/><div className="note-footer"><span>Saved to your {period.type} view</span><button className="text-button" onClick={saveNote}>Save notes</button></div></section>
          <section className="panel goals-panel"><div className="panel-heading"><div><span className="panel-kicker">WHAT MATTERS</span><h2>{view === 'month' ? 'Monthly goals' : 'Goals in focus'}</h2></div><button className="icon-button" aria-label="Add goal" onClick={() => setGoalOpen(true)}><Plus size={17}/></button></div>
            {goals.length ? <div className="goal-list">{goals.slice(0, 4).map(g => <GoalCard key={g.id} goal={g}/>)}</div> : <EmptyState title="No goals yet" body="Connect your tasks to something meaningful." action="Create a goal" onClick={() => setGoalOpen(true)}/>}
          </section>
        </div>}
      </div>
    </main>

    {quickOpen && <Modal title="Add a task" onClose={() => setQuickOpen(false)}><form className="modal-form" onSubmit={submitTask}>
      <label>What needs doing?<input autoFocus value={taskTitle} onChange={e => setTaskTitle(e.target.value)} placeholder="e.g. Go to the gym" required maxLength={180}/></label>
      <div className="form-row"><label>Date<input type="date" value={taskDate} min={todayISO} onChange={e => setTaskDate(e.target.value)} required/></label><label>Priority<select value={taskPriority} onChange={e => setTaskPriority(e.target.value as any)}><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select></label></div>
      <div className="form-row"><label>Category<select value={taskCategory} onChange={e => setTaskCategory(e.target.value)}><option value="">General</option>{categories.filter(c => !c.is_default).map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label><label>Repeat<select value={recurrence} onChange={e => setRecurrence(e.target.value)}><option value="none">Does not repeat</option><option value="daily">Every day</option><option value="weekly">Selected weekdays</option><option value="weekly_count">Flexible times per week</option><option value="monthly">Monthly</option><option value="custom">Every N days</option></select></label></div>
      {recurrence === 'weekly' && <div className="weekday-picker">{['M','T','W','T','F','S','S'].map((d, i) => <button type="button" key={i} className={weekdays.includes(i) ? 'weekday selected' : 'weekday'} onClick={() => setWeekdays(old => old.includes(i) ? old.filter(x => x !== i) : [...old, i])}>{d}</button>)}</div>}
      {recurrence === 'weekly_count' && <label>Target completions per week<input type="number" min="1" max="7" value={weeklyTarget} onChange={e => setWeeklyTarget(Number(e.target.value))}/></label>}
      {recurrence === 'custom' && <label>Repeat every (days)<input type="number" min="1" max="365" value={intervalDays} onChange={e => setIntervalDays(Number(e.target.value))}/></label>}
      <label>Link to a goal (optional)<select value={linkedGoal} onChange={e => setLinkedGoal(e.target.value)}><option value="">No goal</option>{allGoals.map(g => <option key={g.id} value={g.id}>{g.title}</option>)}</select></label>
      <div className="modal-actions"><button type="button" className="secondary-button" onClick={() => setQuickOpen(false)}>Cancel</button><button className="primary-button" disabled={busy}>{busy ? 'Saving…' : 'Add to plan'}</button></div>
    </form></Modal>}

    {categoryOpen && <Modal title="Create a category" onClose={() => setCategoryOpen(false)}><form className="modal-form" onSubmit={addCategory}><label>Category name<input autoFocus value={categoryName} onChange={e => setCategoryName(e.target.value)} placeholder="e.g. Health & fitness" required/></label><label>Category colour<div className="color-input-wrap"><input type="color" value={categoryColor} onChange={e => setCategoryColor(e.target.value)}/><span>{categoryColor.toUpperCase()}</span></div></label><div className="modal-actions"><button type="button" className="secondary-button" onClick={() => setCategoryOpen(false)}>Cancel</button><button className="primary-button">Create category</button></div></form></Modal>}

    {goalOpen && <Modal title="Create a goal" onClose={() => setGoalOpen(false)}><form className="modal-form" onSubmit={addGoal}><label>What do you want to achieve?<input autoFocus value={goalTitle} onChange={e => setGoalTitle(e.target.value)} placeholder="e.g. Go to the gym three times" required/></label><label>Goal level<select value={goalLevel} onChange={e => setGoalLevel(e.target.value)}><option value="weekly">Weekly goal</option><option value="monthly">Monthly goal</option><option value="parent">Larger / parent goal</option></select></label><div className="form-row"><label>Starts<input type="date" value={goalStart} onChange={e => setGoalStart(e.target.value)} required/></label><label>Due date<input type="date" value={goalDue} onChange={e => setGoalDue(e.target.value)} min={goalStart} required/></label></div><label>Parent goal (optional)<select value={goalParent} onChange={e => setGoalParent(e.target.value)}><option value="">No parent goal</option>{allGoals.map(g => <option key={g.id} value={g.id}>{g.title}</option>)}</select></label><div className="task-link-picker"><span className="field-title">Connect existing tasks</span>{tasks.filter(t => t.status === 'open').slice(0, 12).map(t => <label className="link-task" key={t.id}><input type="checkbox" checked={goalTaskIds.includes(t.id)} onChange={e => setGoalTaskIds(old => e.target.checked ? [...old, t.id] : old.filter(id => id !== t.id))}/><span>{t.title}</span><small>{t.scheduled_date}</small></label>)}{!tasks.length && <p className="hint-line">Create tasks first, then connect them to this goal.</p>}</div><div className="modal-actions"><button type="button" className="secondary-button" onClick={() => setGoalOpen(false)}>Cancel</button><button className="primary-button">Create goal</button></div></form></Modal>}

    {editingTask && <Modal title="Edit task" onClose={() => setEditingTask(null)}><form className="modal-form" onSubmit={saveEdit}>
      <label>Task title<input autoFocus value={editTitle} onChange={e => setEditTitle(e.target.value)} required/></label>
      <div className="form-row"><label>Priority<select value={editPriority} onChange={e => setEditPriority(e.target.value as any)}><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select></label><label>Category<select value={editCategory} onChange={e => setEditCategory(e.target.value)}>{categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label></div>
      <p className="hint-line">This updates the task series, including its other scheduled occurrences.</p>
      <div className="modal-actions"><button type="button" className="secondary-button" onClick={() => setEditingTask(null)}>Cancel</button><button className="primary-button">Save changes</button></div>
    </form></Modal>}

    {moveTask && <Modal title="Move task" onClose={() => setMoveTask(null)}><div className="modal-form"><p className="move-title">{moveTask.title}</p><label>Move to date<input type="date" min={todayISO} value={moveDate} onChange={e => setMoveDate(e.target.value)}/></label><div className="modal-actions"><button className="secondary-button" onClick={() => setMoveTask(null)}>Cancel</button><button className="primary-button" onClick={() => move(moveTask, moveDate)}>Move task</button></div></div></Modal>}
  </div>
}

function AuthScreen(props: any) {
  const { email, setEmail, password, setPassword, fullName, setFullName, isRegister, setIsRegister, authenticate, busy, error } = props
  return <div className="auth-shell"><div className="auth-showcase"><div className="brand light"><div className="brand-mark"><Sparkles size={19}/></div><div><strong>daymark</strong><span>make room for progress</span></div></div><div className="showcase-copy"><div className="eyebrow light-eyebrow">A CALMER WAY TO GET THINGS DONE</div><h1>Make space for what <em>matters.</em></h1><p>Bring your daily tasks, habits and bigger goals into one thoughtful workspace.</p><div className="showcase-metrics"><div><strong>01</strong><span>Plan with intention</span></div><div><strong>02</strong><span>Build steady habits</span></div><div><strong>03</strong><span>See your progress</span></div></div></div><div className="showcase-footer">A little progress, consistently.</div></div><div className="auth-form-wrap"><form className="auth-form" onSubmit={authenticate}><span className="panel-kicker">YOUR PERSONAL WORKSPACE</span><h2>{isRegister ? 'Create your account' : 'Welcome back'}</h2><p>{isRegister ? 'Start with a clear view of what matters.' : 'Pick up where you left off.'}</p>{error && <div className="inline-error">{error}</div>}{isRegister && <label>Your name<input value={fullName} onChange={e => setFullName(e.target.value)} placeholder="Name" required/></label>}<label>Email address<input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" required/></label><label>Password<input type="password" minLength={8} value={password} onChange={e => setPassword(e.target.value)} placeholder="At least 8 characters" required/></label><button className="primary-button auth-submit" disabled={busy}>{busy ? 'Please wait…' : isRegister ? 'Create workspace' : 'Sign in'}<ArrowRight size={16}/></button><div className="auth-switch">{isRegister ? 'Already have an account?' : 'New to Daymark?'} <button type="button" onClick={() => setIsRegister(!isRegister)}>{isRegister ? 'Sign in' : 'Create account'}</button></div><div className="auth-footnote"><CheckCircle2 size={14}/> Your plans are stored securely in your own workspace.</div></form></div></div>
}

function NavButton({ active, icon, label, onClick }: { active: boolean; icon: ReactNode; label: string; onClick: () => void }) { return <button className={active ? 'nav-button active' : 'nav-button'} onClick={onClick}>{icon}<span>{label}</span>{active && <span className="nav-active-dot"/>}</button> }
function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) { return <div className="modal-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) onClose() }}><div className="modal"><div className="modal-header"><h2>{title}</h2><button className="icon-button" onClick={onClose}><X size={17}/></button></div>{children}</div></div> }
function EmptyState({ title, body, action, onClick }: { title: string; body: string; action: string; onClick: () => void }) { return <div className="empty-state"><div className="empty-icon"><Sparkles size={18}/></div><strong>{title}</strong><p>{body}</p><button className="text-button" onClick={onClick}>{action} <ArrowRight size={14}/></button></div> }

function TaskRow({ task, onToggle, onMove, onEdit, draggable = false }: { task: Task; onToggle: (task: Task) => void; onMove: (task: Task) => void; onEdit?: (task: Task) => void; draggable?: boolean }) {
  const isPast = task.scheduled_date < todayISO
  return <div className={`task-row ${task.completed ? 'completed' : ''}`} draggable={draggable && !task.completed} onDragStart={e => e.dataTransfer.setData('taskId', String(task.id))}>
    <button className={`task-check ${task.completed ? 'checked' : ''}`} disabled={isPast} onClick={() => onToggle(task)} aria-label={task.completed ? 'Mark incomplete' : 'Mark complete'}>{task.completed && <Check size={13}/>}</button>
    <div className="task-main"><span className="task-title">{task.title}</span><div className="task-meta"><span className="task-category" style={{ color: task.category_color }}><i style={{ background: task.category_color }}/>{task.category_name}</span><span className={`priority-tag ${task.priority}`}>{task.priority}</span></div></div>
    {isPast && <span className="overdue-label">Overdue</span>}
    {!task.completed && !isPast && <button className="task-more" title="Edit task" onClick={() => onEdit?.(task)}><Pencil size={13}/></button>}
    {!task.completed && <button className="task-more" title="Move task" onClick={() => onMove(task)}><ArrowRight size={15}/></button>}
  </div>
}

function DailyView({ selected, visibleOn, categories, overdue, toggleTask, setMoveTask, openEdit }: any) {
  const dayTasks: Task[] = visibleOn(selected)
  const done = dayTasks.filter(t => t.completed).length
  const pct = dayTasks.length ? Math.round(done / dayTasks.length * 100) : 0
  return <div className="daily-layout"><div className="daily-summary panel"><div><span className="panel-kicker">DAILY MOMENTUM</span><h2>{done} <span>/ {dayTasks.length}</span> tasks complete</h2><p>{dayTasks.length ? (pct === 100 ? 'You made it happen. Take a moment to enjoy that.' : 'Keep your focus on the next small step.') : 'A clear day is a good place to begin.'}</p></div><div className="progress-ring" style={{ background: `conic-gradient(#329c88 ${pct}%, #e7eeeb ${pct}% 100%)` }}><div><strong>{pct}%</strong><span>done</span></div></div></div>
    {overdue.length > 0 && <section className="panel overdue-panel"><div className="panel-heading"><div><span className="panel-kicker">CARRY FORWARD</span><h2>Unfinished from earlier</h2></div><span className="count-badge">{overdue.length}</span></div><p className="panel-subtext">Past days are read-only. Move anything unfinished to today or another future date.</p>{overdue.slice(0, 4).map((t: Task) => <TaskRow key={t.id} task={t} onToggle={toggleTask} onMove={setMoveTask} onEdit={openEdit}/>)}</section>}
    <div className="section-heading"><div><span className="panel-kicker">YOUR DAY, IN FOCUS</span><h2>Tasks by category</h2></div><span className="small-muted">{dayTasks.length} planned</span></div>
    {categories.filter((c: Category) => dayTasks.some(t => t.category_id === c.id)).map((cat: Category) => <section className="category-bucket" key={cat.id}><div className="bucket-heading"><span className="bucket-colour" style={{ background: cat.color }}/><h3 style={{ color: cat.color }}>{cat.name}</h3><span>{dayTasks.filter(t => t.category_id === cat.id).length}</span></div>{dayTasks.filter(t => t.category_id === cat.id).map(t => <TaskRow key={t.id} task={t} onToggle={toggleTask} onMove={setMoveTask} onEdit={openEdit}/>)}</section>)}
    {!dayTasks.length && <div className="panel empty-day"><EmptyState title="Nothing planned yet" body="Add a task and give your day a little direction." action="Add a task" onClick={() => window.dispatchEvent(new CustomEvent('open-quick-add'))}/></div>}
  </div>
}

function WeeklyView({ weekStart, visibleOn, selectedDate, setSelectedDate, dropOnDate, tasks, toggleTask, setMoveTask, openEdit, beginDrag }: any) {
  const weekDays = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i))
  const weekTasks: Task[] = tasks.filter((t: Task) => t.scheduled_date >= iso(weekStart) && t.scheduled_date <= iso(addDays(weekStart, 6)) && t.status === 'open')
  const todayTasks: Task[] = visibleOn(fromISO(todayISO))
  const high = weekTasks.filter(t => t.priority === 'high')
  const done = tasks.filter((t: Task) => t.scheduled_date >= iso(weekStart) && t.scheduled_date <= iso(addDays(weekStart, 6)) && t.completed).length
  return <div className="week-layout"><div className="stat-strip"><StatCard label="Completed this week" value={done} icon={<CheckCircle2/>} tint="mint"/><StatCard label="High priority" value={high.length} icon={<Zap/>} tint="amber"/><StatCard label="Tasks today" value={todayTasks.length} icon={<Clock3/>} tint="blue"/></div><section className="panel week-board"><div className="panel-heading"><div><span className="panel-kicker">WEEK AT A GLANCE</span><h2>Move things around as life changes</h2></div><span className="drag-hint">Drag a task to another day</span></div><div className="week-columns">{weekDays.map(day => { const key = iso(day); const items: Task[] = visibleOn(day); return <div className={`week-day ${key === selectedDate ? 'selected-day' : ''} ${key === todayISO ? 'is-today' : ''}`} key={key} onDragOver={e => e.preventDefault()} onDrop={e => dropOnDate(e, key)} onClick={() => setSelectedDate(key)}><div className="week-day-head"><span>{dayLabel(day)}</span><strong>{day.getDate()}</strong></div><div className="week-day-items">{items.slice(0, 5).map(t => <div draggable={!t.completed && key >= todayISO} onDragStart={e => beginDrag(e, t)} className={`mini-task ${t.completed ? 'done' : ''}`} key={t.id} style={{ borderLeftColor: t.category_color }} title={t.title}>{t.title}</div>)}{items.length > 5 && <small>+{items.length - 5} more</small>}{!items.length && <small className="no-items">Drop here</small>}</div></div> })}</div></section><div className="panel priority-panel"><div className="panel-heading"><div><span className="panel-kicker">FOCUS FIRST</span><h2>Priority tasks for today</h2></div><span className="priority-count">{todayTasks.filter(t => t.priority === 'high').length} high priority</span></div>{todayTasks.filter(t => t.priority === 'high').length ? todayTasks.filter(t => t.priority === 'high').map(t => <TaskRow key={t.id} task={t} onToggle={toggleTask} onMove={setMoveTask} onEdit={openEdit}/>) : <p className="panel-subtext">No high-priority tasks today. Keep it that way, or add one when needed.</p>}</div></div>
}

function MonthlyView({ selected, monthStart, visibleOn, selectedDate, setSelectedDate, dropOnDate, beginDrag, tasks, analytics }: any) {
  const gridStart = startOfWeek(monthStart)
  const days = Array.from({ length: 42 }, (_, i) => addDays(gridStart, i))
  return <div className="month-layout">{analytics && <div className="stat-strip four"><StatCard label="Completed this month" value={analytics.completed_tasks} icon={<CheckCircle2/>} tint="mint"/><StatCard label="Completion rate" value={`${analytics.completion_rate}%`} icon={<Activity/>} tint="blue"/><StatCard label="Goals achieved" value={analytics.goals_achieved} icon={<Flag/>} tint="violet"/><StatCard label="Overdue tasks" value={analytics.overdue_tasks} icon={<Clock3/>} tint="amber"/></div>}<div className="panel month-board"><div className="month-weekdays">{['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].map(x => <div key={x}>{x}</div>)}</div><div className="month-grid">{days.map(day => { const key = iso(day); const items: Task[] = visibleOn(day); const isCurrentMonth = day.getMonth() === selected.getMonth(); return <div key={key} className={`month-cell ${!isCurrentMonth ? 'outside-month' : ''} ${key === selectedDate ? 'selected-cell' : ''} ${key === todayISO ? 'today-cell' : ''}`} onClick={() => setSelectedDate(key)} onDragOver={e => e.preventDefault()} onDrop={e => dropOnDate(e, key)}><div className="month-cell-top"><span>{day.getDate()}</span>{items.length > 0 && <small>{items.length} task{items.length > 1 ? 's' : ''}</small>}</div><div className="month-cell-tasks">{items.slice(0, 3).map(t => <div draggable={!t.completed && key >= todayISO} onDragStart={e => beginDrag(e, t)} key={t.id} className={`month-task ${t.completed ? 'done' : ''}`} style={{ '--task-colour': t.category_color } as CSSProperties} title={t.title}>{t.title}</div>)}{items.length > 3 && <small className="more-tasks">+{items.length - 3} more</small>}</div></div>})}</div></div><div className="month-footer-hint"><span><i className="legend-dot"/> Selected date: <strong>{fullDate(fromISO(selectedDate))}</strong></span><span>Drag tasks onto another date to reschedule</span></div></div>
}

function ProgressView({ analytics, goals }: { analytics: Analytics | null; goals: Goal[] }) {
  if (!analytics) return <div className="panel loading-panel">Loading your progress…</div>
  const maxDay = Math.max(1, ...analytics.by_day.map(x => x.total))
  const maxCat = Math.max(1, ...analytics.completed_by_category.map(x => x.completed))
  return <div className="progress-layout"><div className="stat-strip four"><StatCard label="Tasks completed" value={analytics.completed_tasks} icon={<CheckCircle2/>} tint="mint"/><StatCard label="Completion rate" value={`${analytics.completion_rate}%`} icon={<Activity/>} tint="blue"/><StatCard label="Goals achieved" value={analytics.goals_achieved} icon={<Flag/>} tint="violet"/><StatCard label="Overdue tasks" value={analytics.overdue_tasks} icon={<Clock3/>} tint="amber"/></div><div className="analytics-grid"><section className="panel chart-panel"><div className="panel-heading"><div><span className="panel-kicker">CONSISTENCY</span><h2>Daily task activity</h2></div><span className="chart-caption">Scheduled tasks by day</span></div>{analytics.by_day.length ? <div className="bar-chart">{analytics.by_day.map(day => <div className="bar-column" key={day.date}><div className="bar-track"><div className="bar-total" style={{ height: `${day.total / maxDay * 100}%` }}><div className="bar-complete" style={{ height: `${day.total ? day.completed / day.total * 100 : 0}%` }}/></div></div><span>{fromISO(day.date).toLocaleDateString(undefined, { day: 'numeric' })}</span></div>)}</div> : <div className="chart-empty">Task activity will appear here once you start planning.</div>}<div className="chart-legend"><span><i className="legend-complete"/>Completed</span><span><i className="legend-pending"/>Still open</span></div></section><section className="panel chart-panel"><div className="panel-heading"><div><span className="panel-kicker">WHERE YOUR TIME GOES</span><h2>By category</h2></div></div>{analytics.completed_by_category.length ? <div className="category-bars">{analytics.completed_by_category.map(row => <div className="category-bar-row" key={row.category}><div><span>{row.category}</span><strong>{row.completed}</strong></div><div className="category-track"><i style={{ width: `${row.completed / maxCat * 100}%` }}/></div></div>)}</div> : <div className="chart-empty">Complete a task to see your category breakdown.</div>}</section></div><section className="panel habit-overview"><div className="panel-heading"><div><span className="panel-kicker">REPEATABLE ROUTINES</span><h2>Habit progress in this period</h2></div><span className="small-muted">Completed vs expected</span></div>{analytics.habits.length ? <div className="habit-list">{analytics.habits.map(h => <div className="habit-row" key={h.series_id}><div className="habit-info"><strong>{h.title}</strong><span>{h.category} · {h.recurrence_type === 'weekly_count' ? `${h.weekly_target} times / week target` : h.recurrence_type}</span></div><div className="habit-meter"><div className="goal-progress-track"><i style={{ width: `${h.progress}%` }}/></div><b>{h.completed_occurrences}/{h.expected_completions}</b></div><strong className="habit-percent">{h.progress}%</strong></div>)}</div> : <p className="panel-subtext">Recurring tasks will appear here, with completion measured over the selected period.</p>}</section><section className="panel goals-overview"><div className="panel-heading"><div><span className="panel-kicker">INTENTIONS INTO ACTION</span><h2>Goal progress</h2></div><span className="small-muted">{goals.length} active parent goals</span></div>{goals.length ? <div className="goal-grid">{goals.map(g => <GoalCard key={g.id} goal={g}/>)}</div> : <p className="panel-subtext">Create a weekly or monthly goal and link tasks to watch progress update automatically.</p>}</section></div>
}
function StatCard({ label, value, icon, tint }: any) { return <div className="stat-card"><div className={`stat-icon ${tint}`}>{icon}</div><div><span>{label}</span><strong>{value}</strong></div></div> }
function GoalCard({ goal }: { goal: Goal }) { return <div className="goal-card"><div className="goal-card-top"><span className={`goal-level ${goal.level}`}>{goal.level}</span>{goal.achieved && <span className="achieved"><CheckCircle2 size={13}/> Achieved</span>}</div><strong>{goal.title}</strong><div className="goal-progress-line"><div className="goal-progress-track"><i style={{ width: `${goal.progress}%` }}/></div><b>{goal.progress}%</b></div><div className="goal-card-foot"><span>{goal.completed} of {goal.total} linked tasks</span><span>Due {fromISO(goal.due_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</span></div></div> }

export default App
