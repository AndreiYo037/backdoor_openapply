export function expandQuery(role: string): string[] {
  const r = role.toLowerCase();

  if (r.includes("machine learning")) {
    return [
      "machine learning intern singapore",
      "ml intern",
      "ai intern",
      "data science intern",
    ];
  }

  return [
    `${role} intern`,
    `${role} internship`,
    `${role} intern singapore`,
  ];
}
