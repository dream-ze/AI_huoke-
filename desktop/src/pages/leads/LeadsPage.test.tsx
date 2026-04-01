import { MemoryRouter } from "react-router-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LeadsPage } from "./LeadsPage";

const api = vi.hoisted(() => ({
  assignLeadOwner: vi.fn(),
  convertLeadToCustomer: vi.fn(),
  listLeads: vi.fn(),
  updateLeadStatus: vi.fn(),
}));

vi.mock("../../lib/api", () => api);

describe("LeadsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.listLeads.mockResolvedValue([
      {
        id: 201,
        owner_id: 7,
        publish_task_id: 88,
        platform: "douyin",
        title: "线索标题",
        customer_id: null,
        wechat_adds: 2,
        leads: 1,
        valid_leads: 1,
        conversions: 0,
        status: "new",
      },
    ]);
    api.updateLeadStatus.mockResolvedValue({ id: 201, status: "qualified" });
    api.assignLeadOwner.mockResolvedValue({ id: 201, owner_id: 7 });
    api.convertLeadToCustomer.mockResolvedValue({ id: 301, lead_id: 201 });
    vi.spyOn(window, "prompt").mockReturnValue("测试客户");
  });

  it("renders lead rows from API", async () => {
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <LeadsPage />
      </MemoryRouter>,
    );

    expect(await screen.findByText("线索池")).toBeInTheDocument();
    expect(await screen.findByText("线索标题")).toBeInTheDocument();
    expect(api.listLeads).toHaveBeenCalled();
  });

  it("updates lead status and converts to customer", async () => {
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <LeadsPage />
      </MemoryRouter>,
    );

    await screen.findByText("线索标题");

    fireEvent.change(screen.getByDisplayValue("new"), { target: { value: "qualified" } });
    await waitFor(() => expect(api.updateLeadStatus).toHaveBeenCalledWith(201, "qualified"));

    fireEvent.click(screen.getByRole("button", { name: "转客户" }));
    await waitFor(() =>
      expect(api.convertLeadToCustomer).toHaveBeenCalledWith(201, {
        nickname: "测试客户",
      }),
    );
  });
});
