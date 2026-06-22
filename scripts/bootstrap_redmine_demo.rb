Setting.rest_api_enabled = "1"
Setting.host_name = "localhost:3000"
Setting.protocol = "http"

if Tracker.count.zero? || IssueStatus.count.zero? || IssuePriority.count.zero?
  Redmine::DefaultData::Loader.load("en")
end

admin = User.find_by_login("admin") || User.where(admin: true).first || User.first
raise "admin user not found" unless admin

admin.admin = true
admin.status = Principal::STATUS_ACTIVE if defined?(Principal::STATUS_ACTIVE)
admin.password = "Admin123!"
admin.password_confirmation = "Admin123!"
admin.must_change_passwd = false if admin.respond_to?(:must_change_passwd=)
admin.save!

project = Project.find_or_initialize_by(identifier: "budgetbot")
project.name = "BudgetBot"
project.description = "Demo project for Redmine AI Technical Planner."
project.is_public = false
project.status = Project::STATUS_ACTIVE
project.save!

tracker = Tracker.first
project.trackers = [tracker] if project.trackers.empty? && tracker

role = Role.find_by(name: "Manager") || Role.where(builtin: 0).first
if role && !Member.exists?(project_id: project.id, user_id: admin.id)
  Member.create!(project: project, principal: admin, roles: [role])
end

issue = Issue.find_or_initialize_by(
  project: project,
  subject: "Demo: add transaction category filter"
)
issue.tracker ||= tracker
issue.status ||= IssueStatus.first
issue.priority ||= IssuePriority.default || IssuePriority.first
issue.author ||= admin
issue.description = <<~TEXT
  Need to add a category filter to the BudgetBot transaction list.

  Expected behavior:
  - user can filter transactions by category;
  - selected category affects only the visible transaction list;
  - existing add/edit transaction behavior must keep working.

  Please identify likely files and write an implementation plan.
TEXT
issue.save!

token = Token.find_by(user: admin, action: "api")
token ||= Token.create!(user: admin, action: "api", value: Token.generate_token_value)
File.write("/usr/src/redmine/files/redmine_api_key.txt", token.value)
File.write(
  "/usr/src/redmine/files/bootstrap_info.txt",
  "project_identifier=#{project.identifier}\nissue_id=#{issue.id}\n"
)

puts "project_identifier=#{project.identifier}"
puts "issue_id=#{issue.id}"
