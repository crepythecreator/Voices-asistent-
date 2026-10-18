import type { User } from "../model/types";

export function UserAvatar({ user }: { user: User }) {
  return user.avatarUrl ? (
    <img src={user.avatarUrl} alt={user.name} className="size-8 rounded-full" />
  ) : (
    <div className="flex size-8 items-center justify-center rounded-full bg-muted text-sm font-medium" title={user.name}>
      {user.name.slice(0, 1)}
    </div>
  );
}
