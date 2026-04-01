import { MemoryRouter } from "react-router-dom";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PublishPage } from "./PublishPage";

const api = vi.hoisted(() => ({
  assignPublishTask: vi.fn(),
  claimPublishTask: vi.fn(),
  closePublishTask: vi.fn(),
  createPublishTask: vi.fn(),
  exportPublishTasksCsv: vi.fn(),
  getPublishContentAnalysis: vi.fn(),
  getPublishRoiTrend: vi.fn(),
  getPublishStatsByPlatform: vi.fn(),
  getCurrentUser: vi.fn(),
  getPublishTaskTrace: vi.fn(),
  getPublishTaskStats: vi.fn(),
  listPublishTasks: vi.fn(),
  listActiveUsers: vi.fn(),
  listSocialAccounts: vi.fn(),
  rejectPublishTask: vi.fn(),
  submitPublishTask: vi.fn(),
}));

vi.mock("../lib/api", () => api);

describe("PublishPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.getCurrentUser.mockResolvedValue({ id: 7, username: "owner" });
    api.listActiveUsers.mockResolvedValue([{ id: 7, username: "owner", role: "admin", is_active: true }]);
    api.getPublishTaskStats.mockResolvedValue({
      total: 1,
      pending: 1,
      claimed: 0,
      submitted: 0,
      rejected: 0,
      closed: 0,
    });
    api.listPublishTasks.mockResolvedValue([
      {
        id: 101,
        owner_id: 7,
        assigned_to: null,
        platform: "xiaohongshu",
        account_name: "主账号",
        task_title: "待发布任务",
        status: "pending",
        wechat_adds: 0,
        leads: 0,
        conversions: 0,
      },
    ]);
    api.getPublishStatsByPlatform.mockResolvedValue([]);
    api.getPublishRoiTrend.mockResolvedValue([]);
    api.getPublishContentAnalysis.mockResolvedValue([]);
    api.listSocialAccounts.mockResolvedValue([]);
    api.createPublishTask.mockResolvedValue({ id: 102 });
    api.exportPublishTasksCsv.mockResolvedValue({ blob: new Blob(["ok"]) });
  });

  it("renders stats and task list from API", async () => {
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <PublishPage />
      </MemoryRouter>,
    );

    expect(await screen.findByText("发布任务中心")).toBeInTheDocument();
    expect(await screen.findByText("待发布任务")).toBeInTheDocument();
    expect(await screen.findByText("总任务")).toBeInTheDocument();
    expect(await screen.findByText("主账号")).toBeInTheDocument();
    expect(api.getPublishTaskStats).toHaveBeenCalled();
    expect(api.listPublishTasks).toHaveBeenCalled();
  });

  it("submits create task form with cleaned payload", async () => {
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <PublishPage />
      </MemoryRouter>,
    );

    const createSection = (await screen.findByText("创建发布任务")).closest("section");
    expect(createSection).not.toBeNull();
    const textboxes = within(createSection as HTMLElement).getAllByRole("textbox");

    fireEvent.change(textboxes[1], { target: { value: "新测试任务" } });
    fireEvent.change(textboxes[2], { target: { value: "这里是一段待发布内容" } });
    fireEvent.click(within(createSection as HTMLElement).getByRole("button", { name: "创建任务" }));

    await waitFor(() =>
      expect(api.createPublishTask).toHaveBeenCalledWith({
        platform: "xiaohongshu",
        account_name: "主账号",
        task_title: "新测试任务",
        content_text: "这里是一段待发布内容",
        rewritten_content_id: undefined,
      }),
    );
    expect(await screen.findByText("发布任务已创建，可直接领取执行")).toBeInTheDocument();
  });
});
