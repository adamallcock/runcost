const BASE_PATH = (import.meta.env.BASE_URL || "/").replace(/\/$/, "");

export function appPath(path = "/") {
  if (!path.startsWith("/")) return path;
  return `${BASE_PATH}${path}` || "/";
}
