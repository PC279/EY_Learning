export type User = { id: number; email: string; full_name: string; timezone: string; week_start: number }
export type Category = { id: number; name: string; color: string; is_default: boolean }
export type Task = {
  id: number; series_id: number; title: string; description: string; priority: 'high' | 'medium' | 'low'
  category_id: number; category_name: string; category_color: string; scheduled_date: string; status: string
  completed: boolean; recurrence_type: string; weekly_target: number; weekdays: number[]; moved_from_id: number | null
}
export type Goal = {
  id: number; title: string; description: string; level: string; start_date: string; due_date: string
  parent_goal_id: number | null; progress: number; completed: number; total: number; achieved: boolean
  children: Goal[]; linked_task_ids: number[]
}
export type Analytics = {
  total_tasks: number; completed_tasks: number; completion_rate: number; overdue_tasks: number; goals_achieved: number
  by_day: { date: string; total: number; completed: number }[]
  completed_by_category: { category: string; completed: number }[]
  habits: { series_id: number; title: string; category: string; recurrence_type: string; weekly_target: number; scheduled_occurrences: number; completed_occurrences: number; expected_completions: number; progress: number }[]
}
