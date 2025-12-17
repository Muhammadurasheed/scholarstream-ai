import { useState } from 'react';
import { Calendar, Clock, Bookmark, Award, ExternalLink, MapPin } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Scholarship } from '@/types/scholarship';
import {
  formatCurrency,
  getDeadlineInfo,
  getMatchTierColor,
  getPriorityColor,
  getCompetitionBadgeColor,
  isNewScholarship,
} from '@/utils/scholarshipUtils';
import { useNavigate } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';

interface ScholarshipCardProps {
  scholarship: Scholarship;
  isSaved: boolean;
  onToggleSave: (id: string) => void;
  onStartApplication: (id: string) => void;
}

export const ScholarshipCard = ({
  scholarship,
  isSaved,
  onToggleSave,
  onStartApplication,
}: ScholarshipCardProps) => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [imageError, setImageError] = useState(false);
  const deadlineInfo = getDeadlineInfo(scholarship.deadline);
  const isNew = isNewScholarship(scholarship.discovered_at);

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(word => word[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  // Prefetch on hover for instant detail page loads
  const handleMouseEnter = () => {
    import('@/lib/queryClient').then(({ prefetchUtils }) => {
      prefetchUtils.prefetchOpportunityDetail(scholarship.id);
    });
  };

  // Open external application URL
  const handleApplyExternal = (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent card click
    onStartApplication(scholarship.id);

    if (scholarship.source_url) {
      window.open(scholarship.source_url, '_blank', 'noopener,noreferrer');
      toast({
        title: 'Application opened',
        description: 'Use the ScholarStream Copilot extension for AI-assisted applications!',
      });
    } else {
      toast({
        variant: 'destructive',
        title: 'No application link',
        description: 'Application URL not available for this opportunity.',
      });
    }
  };

  const handleToggleSaveWrapper = (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent card click
    onToggleSave(scholarship.id);
  };

  return (
    <Card
      className={cn(
        'group relative flex flex-col h-full overflow-hidden p-5 transition-all duration-200 hover:-translate-y-1 hover:shadow-lg cursor-pointer',
        getPriorityColor(scholarship.priority_level)
      )}
      onMouseEnter={handleMouseEnter}
      onClick={() => navigate(`/opportunity/${scholarship.id}`)}
    >
      {isNew && (
        <div className="absolute right-3 top-3 -rotate-6 z-10">
          <Badge className="bg-success text-success-foreground text-xs px-2 py-0.5">NEW</Badge>
        </div>
      )}

      {/* Header: Logo + Title + Match */}
      <div className="flex items-start gap-3 mb-3">
        {/* Logo */}
        <div className="flex-shrink-0">
          {scholarship.logo_url && !imageError ? (
            <img
              src={scholarship.logo_url}
              alt={scholarship.organization}
              className="h-10 w-10 rounded-lg object-cover"
              onError={() => setImageError(true)}
            />
          ) : (
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <span className="text-xs font-bold">{getInitials(scholarship.organization)}</span>
            </div>
          )}
        </div>

        {/* Title + Org */}
        <div className="flex-1 min-w-0">
          <h3
            className="line-clamp-2 text-base font-semibold text-foreground leading-tight transition-colors group-hover:text-primary"
          >
            {scholarship.name}
          </h3>
          <p className="text-sm text-muted-foreground truncate">{scholarship.organization}</p>
        </div>
      </div>

      {/* Amount Row */}
      <div className="flex items-baseline gap-2 mb-3">
        <span className="text-xl font-bold text-success">{formatCurrency(scholarship.amount)}</span>
        <span className="text-xs text-muted-foreground truncate">{scholarship.amount_display}</span>
      </div>

      {/* Deadline Row */}
      <div className="flex items-center gap-2 mb-3">
        <Calendar className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
        <span className="text-sm text-muted-foreground">{deadlineInfo.formattedDate}</span>
        {deadlineInfo.daysUntil >= 0 && (
          <span className={cn('text-xs font-medium', deadlineInfo.color)}>
            ({deadlineInfo.countdown})
          </span>
        )}
      </div>

      {/* Tags Row */}
      <div className="flex flex-wrap gap-1.5 mb-3">
        {(scholarship.tags || []).slice(0, 3).map((tag, index) => (
          <Badge key={index} variant="secondary" className="text-xs px-2 py-0">
            {tag}
          </Badge>
        ))}
        {(scholarship.tags || []).length > 3 && (
          <Badge variant="secondary" className="text-xs px-2 py-0">
            +{(scholarship.tags || []).length - 3}
          </Badge>
        )}
      </div>

      {/* Metadata Row */}
      <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground mb-4 mt-auto">
        <div className="flex items-center gap-1">
          <Clock className="h-3 w-3" />
          <span>{scholarship.estimated_time}</span>
        </div>
        <Badge
          variant="outline"
          className={cn('text-xs px-1.5 py-0', getCompetitionBadgeColor(scholarship.competition_level))}
        >
          {scholarship.competition_level}
        </Badge>
        <span className="font-medium text-success">
          {(!scholarship.expected_value || isNaN(scholarship.expected_value))
            ? 'Value TBD'
            : `${formatCurrency(scholarship.expected_value)}/hr`}
        </span>
      </div>

      {/* Match Score + Location */}
      <div className="flex items-center justify-between mb-4">
        <Badge className={cn('text-xs', getMatchTierColor(scholarship.match_tier))}>
          {scholarship.match_score}% Match
        </Badge>
        {scholarship.eligibility?.states && (scholarship.eligibility.states || []).length > 0 && (
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <MapPin className="h-3 w-3" />
            <span className="truncate max-w-[100px]">
              {scholarship.eligibility.states[0]}
            </span>
          </div>
        )}
      </div>

      {/* Actions - Always at bottom */}
      <div className="flex items-center gap-2 pt-2 border-t border-border/50">
        <Button
          size="sm"
          variant="outline"
          className="flex-1 text-xs h-8"
          onClick={(e) => {
            e.stopPropagation();
            navigate(`/opportunity/${scholarship.id}`);
          }}
        >
          <ExternalLink className="mr-1.5 h-3.5 w-3.5" />
          Details
        </Button>
        <Button
          size="sm"
          className="flex-1 text-xs h-8"
          onClick={handleApplyExternal}
        >
          Apply Now
        </Button>
        <Button
          size="sm"
          variant="ghost"
          className="h-8 w-8 p-0"
          onClick={handleToggleSaveWrapper}
        >
          <Bookmark
            className={cn('h-4 w-4', isSaved && 'fill-current text-primary')}
          />
        </Button>
      </div>
    </Card>
  );
};
