import { Scholarship } from '@/types/scholarship';
import { AlertTriangle, Clock, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useNavigate } from 'react-router-dom';
import { calculateDaysUntilDeadline } from '@/utils/scholarshipUtils';

interface PriorityAlertsSectionProps {
  urgentScholarships: Scholarship[];
}

export const PriorityAlertsSection = ({ urgentScholarships }: PriorityAlertsSectionProps) => {
  const navigate = useNavigate();

  if (urgentScholarships.length === 0) return null;

  return (
    <section className="mb-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center gap-2 mb-4">
        <div className="p-2 rounded-full bg-red-100 dark:bg-red-900/30">
          <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400" />
        </div>
        <h2 className="text-xl font-bold text-foreground">Priority Alerts</h2>
        <span className="px-2.5 py-0.5 text-xs font-semibold bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300 rounded-full">
          {urgentScholarships.length} Action Required
        </span>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {urgentScholarships.slice(0, 3).map((scholarship) => {
          const daysLeft = calculateDaysUntilDeadline(scholarship.deadline);

          return (
            <div
              key={scholarship.id}
              className="group relative overflow-hidden rounded-xl border border-red-200 bg-red-50/30 p-5 transition-all hover:border-red-300 hover:shadow-md dark:border-red-900/30 dark:bg-red-950/10"
            >
              <div className="absolute top-0 right-0 p-3 opacity-10 group-hover:opacity-20 transition-opacity">
                <Clock className="w-24 h-24 text-red-500" />
              </div>

              <div className="relative z-10">
                <div className="flex justify-between items-start mb-2">
                  <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md bg-white/80 dark:bg-black/40 text-xs font-medium text-red-600 dark:text-red-400 backdrop-blur-sm border border-red-100 dark:border-red-900/50">
                    <Clock className="w-3 h-3" />
                    Expires in {daysLeft} days
                  </span>
                  <span className="font-bold text-green-600 dark:text-green-400">
                    {scholarship.amount_display}
                  </span>
                </div>

                <h3 className="font-bold text-lg mb-1 line-clamp-1 group-hover:text-primary transition-colors">
                  {scholarship.name}
                </h3>
                <p className="text-sm text-muted-foreground mb-4 line-clamp-1">
                  {scholarship.organization}
                </p>

                <div className="flex items-center justify-between mt-auto">
                  <div className="text-xs text-muted-foreground">
                    High Match ({scholarship.match_score}%)
                  </div>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="text-red-600 hover:text-red-700 hover:bg-red-100 dark:text-red-400 dark:hover:bg-red-900/30 p-0 h-auto font-semibold group/btn"
                    onClick={() => navigate(`/opportunity/${scholarship.id}`)}
                  >
                    View Details
                    <ArrowRight className="w-4 h-4 ml-1 transition-transform group-hover/btn:translate-x-1" />
                  </Button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
};
