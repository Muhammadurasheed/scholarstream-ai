import { Clock, DollarSign, MapPin, ArrowRight, Bookmark } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export interface Opportunity {
  id: string;
  title: string;
  organization: string;
  type: "scholarship" | "grant" | "internship" | "research";
  amount?: string;
  deadline: string;
  location?: string;
  description: string;
  isNew?: boolean;
  tags: string[];
}

interface OpportunityCardProps {
  opportunity: Opportunity;
  style?: React.CSSProperties;
}

const typeColors = {
  scholarship: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  grant: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  internship: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  research: "bg-purple-500/10 text-purple-400 border-purple-500/20",
};

export const OpportunityCard = ({ opportunity, style }: OpportunityCardProps) => {
  return (
    <div
      className="group glass rounded-2xl p-6 hover:shadow-lg transition-all duration-300 hover:-translate-y-1 animate-fade-in"
      style={style}
    >
      <div className="flex items-start justify-between gap-4 mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <Badge className={`${typeColors[opportunity.type]} border capitalize`}>
              {opportunity.type}
            </Badge>
            {opportunity.isNew && (
              <Badge variant="live" className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
                New
              </Badge>
            )}
          </div>
          <h3 className="text-lg font-semibold text-foreground group-hover:text-primary transition-colors line-clamp-2">
            {opportunity.title}
          </h3>
          <p className="text-sm text-muted-foreground mt-1">
            {opportunity.organization}
          </p>
        </div>
        <button className="p-2 rounded-lg hover:bg-secondary transition-colors text-muted-foreground hover:text-foreground">
          <Bookmark className="w-5 h-5" />
        </button>
      </div>

      <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
        {opportunity.description}
      </p>

      <div className="flex flex-wrap gap-3 mb-4 text-sm">
        {opportunity.amount && (
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <DollarSign className="w-4 h-4 text-primary" />
            <span>{opportunity.amount}</span>
          </div>
        )}
        <div className="flex items-center gap-1.5 text-muted-foreground">
          <Clock className="w-4 h-4 text-primary" />
          <span>{opportunity.deadline}</span>
        </div>
        {opportunity.location && (
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <MapPin className="w-4 h-4 text-primary" />
            <span>{opportunity.location}</span>
          </div>
        )}
      </div>

      <div className="flex items-center justify-between pt-4 border-t border-border">
        <div className="flex flex-wrap gap-1.5">
          {opportunity.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="px-2 py-0.5 text-xs bg-secondary rounded-md text-muted-foreground"
            >
              {tag}
            </span>
          ))}
        </div>
        <Button variant="ghost" size="sm" className="gap-1 text-primary hover:text-primary">
          View Details
          <ArrowRight className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
};
