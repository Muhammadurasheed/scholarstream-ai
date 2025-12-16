import { TrendingUp, Users, Award, Clock } from "lucide-react";

const stats = [
  { label: "Active Opportunities", value: "2,847", icon: TrendingUp },
  { label: "Students Matched", value: "45K+", icon: Users },
  { label: "Funding Awarded", value: "$12M+", icon: Award },
  { label: "New Today", value: "127", icon: Clock },
];

export const StatsBar = () => {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6">
      {stats.map(({ label, value, icon: Icon }) => (
        <div
          key={label}
          className="glass rounded-xl p-4 md:p-5 text-center hover:shadow-md transition-all duration-300"
        >
          <div className="flex items-center justify-center w-10 h-10 mx-auto mb-3 rounded-lg bg-primary/10">
            <Icon className="w-5 h-5 text-primary" />
          </div>
          <div className="text-2xl md:text-3xl font-bold gradient-text mb-1">
            {value}
          </div>
          <div className="text-xs md:text-sm text-muted-foreground">{label}</div>
        </div>
      ))}
    </div>
  );
};
