// Utility functions for scholarship data processing
import { Scholarship, MatchTier, PriorityLevel } from '@/types/scholarship';
import { differenceInDays, format, formatDistanceToNow } from 'date-fns';

export const formatCurrency = (amount: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
};

export const getDeadlineInfo = (deadline: string) => {
  let deadlineDate = new Date(deadline);
  if (isNaN(deadlineDate.getTime())) {
    deadlineDate = new Date(); // Fallback to today to avoid crash
  }
  const daysUntil = differenceInDays(deadlineDate, new Date());

  let urgency: 'urgent' | 'soon' | 'normal' = 'normal';
  let color: string = 'text-slate-400';

  if (daysUntil < 7) {
    urgency = 'urgent';
    color = 'text-danger';
  } else if (daysUntil < 30) {
    urgency = 'soon';
    color = 'text-warning';
  }

  const formattedDate = format(deadlineDate, 'MMMM d, yyyy');
  const countdown = daysUntil > 0
    ? `Due in ${daysUntil} ${daysUntil === 1 ? 'day' : 'days'}`
    : daysUntil === 0
      ? 'Due today!'
      : 'Deadline passed';

  return { urgency, color, formattedDate, countdown, daysUntil };
};

export const matchTierLabels: Record<string, string> = {
  excellent: 'Excellent Match',
  great: 'Great Match',
  good: 'Good Match',
  fair: 'Fair Match',
  potential: 'Potential Match',
  low: 'Low Match',
  poor: 'Potential Match'
};

export const getMatchTierColor = (tier: MatchTier | string | undefined): string => {
  const tierLower = (tier || 'potential').toLowerCase();
  const colors: Record<string, string> = {
    excellent: 'bg-success text-success-foreground',
    great: 'bg-primary text-primary-foreground',
    good: 'bg-primary text-primary-foreground',
    fair: 'bg-warning text-warning-foreground',
    potential: 'bg-muted text-muted-foreground',
    low: 'bg-muted/50 text-muted-foreground',
    poor: 'bg-muted text-muted-foreground',
  };
  return colors[tierLower] || colors.potential;
};

export const priorityLabels: Record<string, string> = {
  urgent: 'Urgent',
  high: 'High Priority',
  medium: 'Medium Priority',
  low: 'Low Priority'
};

export const getPriorityColor = (priority: PriorityLevel | string | undefined): string => {
  const priorityLower = (priority || 'low').toLowerCase();
  const colors: Record<string, string> = {
    urgent: 'border-l-4 border-danger',
    high: 'border-l-4 border-warning',
    medium: 'border-l-4 border-info',
    low: '',
  };
  return colors[priorityLower] || '';
};

export const calculateDaysUntilDeadline = (deadline: string): number => {
  try {
    if (!deadline) return 365; // Default to far future if missing
    const date = new Date(deadline);
    if (isNaN(date.getTime())) return 365; // Default to far future if invalid

    // Return actual difference, allowing negative values for expired items
    return differenceInDays(date, new Date());
  } catch (e) {
    return 365;
  }
};

export const isNewScholarship = (discoveredAt: string): boolean => {
  const hoursSinceDiscovery = (Date.now() - new Date(discoveredAt).getTime()) / (1000 * 60 * 60);
  return hoursSinceDiscovery < 24;
};

export const getCompetitionBadgeColor = (level: string): string => {
  const colors: Record<string, string> = {
    Low: 'bg-success/20 text-success',
    Medium: 'bg-warning/20 text-warning',
    High: 'bg-danger/20 text-danger',
  };
  return colors[level] || 'bg-muted text-muted-foreground';
};

export const sortScholarships = (
  scholarships: Scholarship[],
  sortBy: string
): Scholarship[] => {
  const sorted = [...scholarships];

  switch (sortBy) {
    case 'best_match':
      return sorted.sort((a, b) => b.match_score - a.match_score);
    case 'deadline':
      return sorted.sort((a, b) => {
        const dateA = new Date(a.deadline).getTime();
        const dateB = new Date(b.deadline).getTime();
        return (isNaN(dateA) ? Infinity : dateA) - (isNaN(dateB) ? Infinity : dateB);
      });
    case 'amount':
    case 'amount_high':
      return sorted.sort((a, b) => b.amount - a.amount);
    case 'amount_low':
      return sorted.sort((a, b) => a.amount - b.amount);
    case 'time':
      return sorted.sort((a, b) => {
        const timeA = parseInt(a.estimated_time) || 0;
        const timeB = parseInt(b.estimated_time) || 0;
        return timeA - timeB;
      });
    case 'recent':
    case 'newest':
      return sorted.sort((a, b) => {
        const dateA = new Date(a.discovered_at).getTime();
        const dateB = new Date(b.discovered_at).getTime();
        return (isNaN(dateB) ? 0 : dateB) - (isNaN(dateA) ? 0 : dateA);
      });
    default:
      return sorted;
  }
};

export const filterScholarshipsByTab = (
  scholarships: Scholarship[],
  tab: string
): Scholarship[] => {
  switch (tab) {
    case 'high_priority':
      return scholarships.filter(s =>
        s.match_score > 70 || calculateDaysUntilDeadline(s.deadline) < 30
      );
    case 'closing_soon':
      return scholarships.filter(s => calculateDaysUntilDeadline(s.deadline) < 30);
    case 'high_value':
      return scholarships.filter(s => s.amount > 10000);
    case 'best_match':
      return scholarships.filter(s => s.match_score > 80);
    default:
      return scholarships;
  }
};

export const getGradeFromGPA = (gpa: number): string => {
  if (gpa >= 3.9) return 'A+';
  if (gpa >= 3.7) return 'A';
  if (gpa >= 3.3) return 'A-';
  if (gpa >= 3.0) return 'B+';
  if (gpa >= 2.7) return 'B';
  if (gpa >= 2.3) return 'B-';
  if (gpa >= 2.0) return 'C+';
  return 'C';
};

export const getTimeAgo = (date: string): string => {
  return formatDistanceToNow(new Date(date), { addSuffix: true });
};
