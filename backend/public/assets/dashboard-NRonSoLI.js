import { t as getJsx } from "./jsx-runtime-bzQ4Vb5N.js";
import { t as Link } from "./link-CVkLs2P8.js";
import { n as useQuery } from "./useMutation-CZFIg5jb.js";
import { i as LogOutIcon, n as MoonIcon, r as SunIcon, t as useTheme } from "./theme-provider-B2F5fZ4I.js";
import { t as GlobeIcon } from "./globe-BNVTW_QW.js";
import { n as ProjectsIcon, t as SettingsIcon } from "./settings-BdwBbH5A.js";
import { t as UsersIcon } from "./users-CG7u0fQJ.js";
import { A as useAuth, W as fetchEpisodes, yt as useRouterState } from "./index-B1NRAZfl.js";
import { component as DashboardInner } from "./dashboard-CiKcVxKv.js";

var jsx = getJsx();

function SidebarNav() {
  let routerState = useRouterState({ select: function(s) { return s.location.pathname; } });
  let currentPath = routerState || "/dashboard";
  let themeObj = useTheme();
  let currentTheme = themeObj.theme;
  let toggleTheme = themeObj.toggle;
  
  let authObj = useAuth();
  let currentUser = authObj.user;
  let currentToken = authObj.token;
  let logoutFn = authObj.logout;

  let queryRes = useQuery({
    queryKey: ["episodes"],
    queryFn: async function() {
      try { return await fetchEpisodes(); } catch(err) { return []; }
    },
    refetchInterval: 5000,
    retry: false
  });

  let episodesList = queryRes.data || [];
  let epCount = episodesList.length;
  let initials = (currentUser && currentUser.name) ? currentUser.name.split(" ").map(function(n){ return n[0]; }).join("").substring(0,2).toUpperCase() : "JL";
  let isSuperAdmin = (currentUser && currentUser.role === "Super Admin") || currentToken === "SUPER_ADMIN" || (currentToken && currentToken.includes("user-1"));

  let navItems = isSuperAdmin ? [
    { icon: UsersIcon, label: "Users & Accounts", to: "/admin" },
    { icon: SettingsIcon, label: "API Configuration", to: "/admin/api-config" }
  ] : [
    { icon: ProjectsIcon, label: "Projects", to: "/dashboard" },
    { icon: GlobeIcon, label: "Connected Apps", to: "/settings?tab=connected-apps" },
    { icon: SettingsIcon, label: "Settings", to: "/settings" }
  ];

  return jsx.jsxs("aside", {
    className: "w-60 border-r border-border flex flex-col shrink-0 bg-background",
    children: [
      jsx.jsx("div", {
        className: "p-6 flex items-center gap-3",
        children: jsx.jsx("img", {
          src: currentTheme === "dark" ? "/logos/podule-wordmark-light.svg" : "/logos/podule-wordmark-dark.svg",
          alt: "Podule",
          className: "h-7 shrink-0"
        })
      }),
      jsx.jsxs("nav", {
        className: "flex-1 px-3 space-y-0.5",
        children: [
          jsx.jsx("div", {
            className: "text-[10px] font-mono text-muted px-3 py-2 tracking-widest",
            children: isSuperAdmin ? "Platform Management" : "Main"
          }),
          navItems.map(function(item) {
            let active = item.to === "/dashboard" ? currentPath === "/dashboard" : currentPath.startsWith(item.to);
            return jsx.jsxs(Link, {
              to: item.to,
              className: "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors " + (active ? "bg-foreground/5 text-foreground font-semibold" : "text-muted hover:text-foreground hover:bg-foreground/[0.03]"),
              children: [
                jsx.jsx(item.icon, { className: "size-4", strokeWidth: 1.75 }),
                jsx.jsx("span", { className: "flex-1", children: item.label }),
                (!isSuperAdmin && item.label === "Projects" && epCount > 0) ? jsx.jsx("span", { className: "text-[10px] font-mono text-muted", children: epCount }) : null
              ]
            }, item.label);
          })
        ]
      }),
      jsx.jsx("div", {
        className: "p-4 border-t border-border space-y-3",
        children: jsx.jsxs("div", {
          className: "flex items-center gap-2 px-1",
          children: [
            jsx.jsx("div", {
              className: "size-7 rounded-full bg-foreground/10 border border-border grid place-items-center text-[10px] font-bold text-foreground shrink-0",
              children: initials
            }),
            jsx.jsxs("div", {
              className: "flex flex-col leading-tight flex-1 min-w-0",
              children: [
                jsx.jsx("span", { className: "text-xs font-medium truncate", title: (currentUser && currentUser.name) || "", children: (currentUser && currentUser.name) || "Jordan Lee" }),
                jsx.jsx("span", { className: "text-[9px] text-muted font-mono truncate", title: (currentUser && currentUser.role) || "", children: (currentUser && currentUser.role) || "Operator" })
              ]
            }),
            jsx.jsxs("div", {
              className: "flex items-center gap-1 shrink-0",
              children: [
                jsx.jsx("button", {
                  onClick: toggleTheme,
                  "aria-label": "Toggle theme",
                  className: "size-7 grid place-items-center rounded-md border border-border hover:bg-foreground/5 transition-colors text-muted hover:text-foreground cursor-pointer",
                  children: currentTheme === "dark" ? jsx.jsx(MoonIcon, { className: "size-3.5" }) : jsx.jsx(SunIcon, { className: "size-3.5" })
                }),
                jsx.jsx("button", {
                  onClick: logoutFn,
                  "aria-label": "Log out",
                  className: "size-7 grid place-items-center rounded-md border border-border hover:bg-foreground/10 hover:border-foreground/20 hover:text-foreground transition-colors text-muted cursor-pointer",
                  children: jsx.jsx(LogOutIcon, { className: "size-3.5" })
                })
              ]
            })
          ]
        })
      })
    ]
  });
}

var S = function() {
  return jsx.jsxs("div", {
    className: "flex h-screen bg-background text-foreground font-sans overflow-hidden",
    children: [
      jsx.jsx(SidebarNav, {}),
      jsx.jsxs("main", {
        className: "flex-1 flex flex-col min-w-0 overflow-hidden",
        children: [
          jsx.jsx(DashboardInner, {})
        ]
      })
    ]
  });
};

export { S as component };
